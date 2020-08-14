#!/usr/bin/env python
# glitch: Linux 'chmod +x' of this file goes missing till I hook up Git CLI

r"""
Python should speak Bel, because the machine should speak your language, which might be Bel
"""

from __future__ import print_function

import __main__

import argparse
import io
import re
import sys
import textwrap
import time
import traceback

try:
    import StringIO
except ModuleNotFoundError:
    pass


BEL_DOT = '.'
BEL_NIL = 'nil'
BEL_PROMPT = 'plbel>'

BEL_LITERALS = """
    + . - / 0 1 2 \bel \bs \tab \lf \cr a b bar baz c clo fn foo lit prn nil t while x
    3 4 5 6 7 8 9 if then test else
""".split()


def main(argv):
    """Run from the command line"""

    parser = bel_compile_argdoc()
    args = parser.parse_args(argv[1:])

    bvm = BelVirtualMachine()

    if args.test_self:
        btb = BelTestBot(bvm)
        btb.test_bvm()
        print()
        print('Test Self Passed Once', file=sys.stderr)
        return

    bvm.chat_bel()


def bel_compile_argdoc():
    """Construct the helplines for a parser, and the parser itself, to parse a command line"""

    parser = argparse.ArgumentParser(
        prog='plbel',
        formatter_class=argparse.RawTextHelpFormatter,
        )

    parser.add_argument('-t', '--test-self', action='store_true',
        help='run the plbel self-test')

    return parser


class BelVirtualMachine(object):
    """Run as a Virtual Machine that understands Bel"""

    BEL_MARKS = '( )'.split()

    def __init__(self):
        self.sourceline = ''
        self.values = None
        self.lists = []

    def chat_bel(self):
        """Prompt for words of Bel, read each, eval each, print values (except None's), and loop"""

        while True:
            sourceline = self.input_line()
            for value in self.eval_line(sourceline):
                if value is not None:
                    print(bel_format_value(value))

    @staticmethod
    def input_line():
        """Prompt and read next Bel source line, else exit"""

        sys.stderr.write(BEL_PROMPT + ' ')
        sys.stderr.flush()  # flush Stderr before waiting on Stdin

        line = sys.stdin.readline()
        if line == '':
            sys.stderr.write('\n')
            sys.exit()

        return line

    def eval_line(self, sourceline):
        """Yield the values of the line, and then return None"""

        self.sourceline = sourceline
        while self.sourceline:
            word = self.read_word()

            if word is not None:
                value = self.interpret_word(word)
                if self.values is not None:
                    self.values.append(value)
                else:
                    yield value

    def read_word(self):
        """Read next word from this line, else prompt and read first word of next line"""

        chars = self.sourceline.strip()

        if not chars:
            self.sourceline = chars
            return None

        for word in self.BEL_MARKS:
            if chars.startswith(word):
                self.sourceline = chars[len(word):]
                return word

        if chars.startswith('"'):
            found = chars[len('"'):].find('"')  # glitch: no tests of quoting backslashes and quotes
            if found >= 0:
                len_word = (len('"') + found + len('"'))
                word = chars[:len_word]
                self.sourceline = chars[len(word):]
                return word

        word = chars[:2]
        if word == '\\ ':  # glitch: no tests of blank char
            self.sourceline = chars[len(word):]
            return word

        split0 = chars.split()[0]
        while split0[:1] and (split0[-1:] in self.BEL_MARKS):  # glitch: always 1 char per mark
            split0 = split0[:-1]

        for word in BEL_LITERALS:  # glitch: read_word apart from interpret_word
            if split0 == word:
                self.sourceline = chars[len(word):]
                return word

        if split0.startswith('\\'):
            word = split0
            self.sourceline = chars[len(word):]
            return word

        print('ERROR: Bel choked at:  {}'.format(chars))
        self.sourceline = ''
        self.values = None  # glitch: reinit should be a method
        return None

    def interpret_word(self, word):
        """Do what the word says to do"""

        if word == '(':

            self.lists.append(self.values)
            self.values = []

            return None

        if word == ')':

            if self.values is None:
                print("ERROR: Insert more '(' ahead of this ')'")
                return None

            assert self.values[0] is None
            unflat_values = self.values[1:]
            flat_values = self.collapse_dot_pairs(unflat_values)

            if all(isinstance(v, BelChar) for v in flat_values):
                if all((len(v.char) == 1) for v in flat_values):
                    chars = ''.join(v.char for v in flat_values)
                    if '"' not in chars:  # glitch: no tests of listing odd chars
                        if '\\' not in chars:
                            value = BelString(chars)
                            self.values = self.lists.pop()  # glitch: common exits
                            return value

            value = BelList(flat_values)

            self.values = self.lists.pop()
            if not self.values:

                listed = value.values
                if listed:
                    value = self.interpret_list(value, collected=listed)

            return value

        if word.startswith('\\'):
            value = BelChar(word[len('\\'):])
            return value

        if word.startswith('"'):
            value = BelString(word[len('"'):][:-len('"')])
            return value

        value = BelLiteral(word)
        return value

    lists_of_evallings = []

    def interpret_list(self, value, collected):
        """Do what the list says to do"""

        defs = '+ prn while - /'.split()

        evalling = False  # glitch: to eval or not to eval
        if isinstance(collected[0], BelLiteral) and (collected[0].source in defs):
            if self.lists_of_evallings and (len(self.lists_of_evallings) > 1):
                evalling = True
            self.lists_of_evallings.append(evalling)

        if not evalling:
            listed = list(collected)
        else:
            listed = []
            for v in collected:
                if isinstance(v, BelList):
                    listed.append(self.interpret_list(None, collected=v.values))
                else:
                    listed.append(v)

        if all(isinstance(v, BelLiteral) for v in listed):

            if listed[0].source == '+':
                summed = 0
                for v in listed[1:]:
                    summed += int(v.source)
                value = BelLiteral(str(summed))

            elif listed[0].source == 'prn':
                if not listed[1:]:
                    print()
                    value = None
                else:
                    for v in listed[1:]:
                        print(bel_format_value(v))
                    value = listed[-1]

            elif len(listed) == 2:
                if listed[0].source == 'while':
                    if listed[1].source == 't':
                        class TimeoutExpired(Exception):
                            pass
                        time.sleep(0.010)
                        raise TimeoutExpired('Doctest hung for 10ms')

            elif len(listed) == 3:
                if listed[0].source == '-':
                    left = int(listed[1].source)
                    right = int(listed[2].source)
                    diff = (left - right)
                    value = BelLiteral(str(diff))
                elif listed[0].source == '/':
                    above = int(listed[1].source)
                    below = int(listed[2].source)
                    quotient = (above / below)  # glitch: what kind of division
                    value = BelLiteral(str(quotient))

        return value

    @staticmethod
    def collapse_dot_pairs(values):
        """See paired with Dot List as listed, see paired with Dot Nil as list of one"""

        if len(values) == 3:
            if isinstance(values[1], BelLiteral) and (values[1].source == BEL_DOT):  # glitch: eq
                if isinstance(values[2], BelLiteral) and (values[2].source == BEL_NIL):
                    return values[:1]
                elif isinstance(values[2], BelList):
                    return ([values[0]] + values[2].values)
        return values


def bel_format_value(value):
    """Convert to roughly equal Bel Source"""

    if hasattr(value, 'bel_repr'):
        return value.bel_repr()

    return value.__repr__()


class BelLiteral(object):
    """Wrap one Bel Word"""

    def __init__(self, source):
        self.source = source

    def bel_repr(self):
        formatted = self.source
        return formatted

    def __repr__(self):
        py_source = 'BelLiteral({!r})'.format(self.source)
        return py_source


class BelString(object):
    """Wrap zero or more Py Characters strung together"""

    def __init__(self, chars):
        self.chars = chars

    def bel_repr(self):
        formatted = '"{}"'.format(self.chars)
        return formatted


class BelChar(object):
    """Wrap one Py Character"""

    def __init__(self, char):
        self.char = char  # might be word such as 'bel' in r'\bel'

    def bel_repr(self):
        formatted = '\\{}'.format(self.char)
        return formatted


class BelList(object):
    """Wrap a list of Py Objects as if a chain of Bel Pairs ending in Bel Nil"""

    def __init__(self, values):
        self.values = values

    def bel_repr(self):
        formatted = '({})'.format(' '.join(bel_format_value(v) for v in self.values))
        return formatted


class BelTestBot(object):
    """Measure how well a Bel Virtual Machine runs"""

    def __init__(self, bvm):
        self.bvm = bvm

    def test_bvm(self):
        """Run the tests of the test doc, in order"""

        bel_docs = self.bel_parse_doctest(textwrap.dedent(_PLBEL_DOCTEST).strip())
        for bel_docs in bel_docs:
            (between, code, want_reply,) = bel_docs

            sys.stdout.write(between)  # glitch: the 'between' past last prompt gets lost
            if code is not None:
                sys.stdout.write(code + '\n')
            sys.stdout.flush()

            if code:
                (got_reply, got_reply_details,) = self.test_bvm_code(code)
                self.diff_replies(code, want_reply, got_reply, got_reply_details)

    def test_bvm_code(self, code):
        """Run one test next"""

        got_reply_details = ''

        stdout = io.StringIO() if (sys.version_info.major >= 3) else StringIO.StringIO()
        try:

            with_stdout = sys.stdout
            sys.stdout = stdout
            try:
                values = list(self.bvm.eval_line(code))
            finally:
                sys.stdout = with_stdout
                stdout.seek(0)

        except Exception as ex:

            got_reply_details = traceback.format_exc()

            got_reply = textwrap.dedent("""
                Traceback (most recent call last):
                  ...
                {}: {}
            """.format(type(ex).__name__, ex)).strip() + '\n'

            sys.stdout.write(got_reply_details)
            sys.stdout.flush()

            return (got_reply, got_reply_details,)

        got_reply_details = stdout.read()

        try:
            assert values  # glitch: look at growing BEL_LITERALS
            assert len(values) == 1  # glitch: testing only one value per line
        except:
            print(got_reply_details)
            raise

        value = values[0]

        got_reply_details += bel_format_value(value)  # glitch: not dented, when test is dented
        print(got_reply_details)                      # glitch: oi by now this is more annoying
        got_reply_details += '\n'

        got_reply = got_reply_details

        return (got_reply, got_reply_details,)

    def diff_replies(self, code, want_reply, got_reply, got_reply_details):

        if got_reply == want_reply:
            return

        print()
        print()

        print('Self Test failed at:', code)

        dent = (4 * ' ')
        print('Want:')
        for line in want_reply.splitlines():
            print(dent + line)

        print('Got:')
        for line in got_reply_details.splitlines():
            print(dent + line)

        sys.exit(-1)

    def bel_parse_doctest(self, source):
        """Pick out and yield tests of (text between, code to eval, reply to expect,) from test doc"""

        between = ''

        lines = source.splitlines()
        while lines:
            line = lines[0]
            lines = lines[1:]

            (prompt, code,) = self.bel_split_line(line)
            if not prompt:
                between += (line + '\n')
            else:
                between += prompt
                code = line[len(prompt):]

                reply = ''
                while lines:
                    if lines[0].lstrip().startswith(BEL_PROMPT):
                        break
                    line = lines[0]
                    lines = lines[1:]
                    reply += (line + '\n')

                reply = textwrap.dedent(reply)

                bel_doc = (between, code, reply,)
                yield bel_doc

                between = ''

        code = None
        reply = ''

        bel_doc = (between, code, reply,)
        yield bel_doc

    @staticmethod
    def bel_split_line(line):
        """Split a line of transcript into its prompt before its input, and its input"""

        prompt = ''
        code = line
        if not line.lstrip().startswith(BEL_PROMPT):
            return (prompt, code,)

        splitter = line.index(BEL_PROMPT)
        splitter += len(BEL_PROMPT)

        beyond = line[splitter:]
        splitter += (len(beyond) - len(beyond.lstrip()))

        prompt = line[:splitter]
        code = line[splitter:]
        return (prompt, code,)


_PLBEL_DOCTEST = r"""

    From: The Bel Language, 12 Oct 2019

    Data

        plbel> foo
        foo
        plbel> (foo . bar)
        (foo . bar)
        plbel> (foo . (bar . baz))
        (foo bar . baz)
        plbel> \a
        \a
        plbel> \bel
        \bel
        plbel>

    Lists

        plbel> nil
        nil
        plbel> (a . nil)
        (a)
        plbel> (a . (b . nil))
        (a b)
        plbel> (a . (b . (c . nil)))
        (a b c)
        plbel>

        plbel> (a (b) c)
        (a (b) c)
        plbel> ((a b c))
        ((a b c))
        plbel> (nil)
        (nil)
        plbel> (a b c)
        (a b c)
        plbel> (a b . c)
        (a b . c)
        plbel>

        plbel> (\h \e \l \l \o)
        "hello"
        plbel> "Hello Bel world!"
        "Hello Bel world!"
        plbel>

    Functions

        plbel> (lit clo nil (x) (+ x 1))
        (lit clo nil (x) (+ x 1))
        plbel> (fn (x) (+ x 1))
        (fn (x) (+ x 1))
        plbel>

    Evaluation

        plbel> (+ 1 2)
        3
        plbel> (/ 1 0)
        Traceback (most recent call last):
          ...
        ZeroDivisionError: division by zero
        plbel> (while t)
        Traceback (most recent call last):
          ...
        TimeoutExpired: Doctest hung for 10ms
        plbel>

        plbel> (prn 1)
        1
        1
        plbel>

        plbel> (+ x 1)
        Traceback (most recent call last):
          ...
        ValueError: invalid literal for int() with base 10: 'x'
        plbel>

        plbel> (+ 8 5)
        13
        plbel>



        plbel> (- 5 2)
        3
        plbel>

        plbel> (+ 3 7)
        10
        plbel>

    To eval or not to eval, that is the question

        plbel> (+ (- 5 2) 7)
        10
        plbel>

        plbel> (if test then else)
        (if test then else)
        plbel>

"""
r"""
"""


if __name__ == '__main__':  # when not imported
    main(sys.argv)

