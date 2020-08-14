#!/usr/bin/env python3

r"""
Convert to Csv Spreadsheet from Pdf Printout of Chase Bank Statements

Work just enough to make some sense of many transactions of my statements
"""


import argparse
import csv
import datetime as dt
import os
import re
import sys
import textwrap


# Focus on pairs of lines tagged as Tj Tm, or as TJ Tm
#
#   Require a leading "Date Of" formatted as fuzzy Mm/Dd
#
#   Accept interruption by an initial Header Row, and redundant Header Rows
#

LEADING_TJ_REGEX = r'^\([0-9][0-9][/][0-9][0-9]\)Tj$'
EXTRA_TJ_REGEX = r'^\(\$ Amount\)Tj$'

PAIRED_TM_REGEX = r'^1 0 0 1 [0-9.]+ [0-9.]+ Tm$'


def main():
    """Convert to Csv Spreadsheet from Pdf Printout of Chase Bank Statements"""

    main.trace = argparse.Namespace()
    when_launched = dt.datetime.now()

    # Export to Csv

    csv_writer = csv.writer(open('chase-export-csv.csv', 'w'))
    #csv_writer = csv.writer(sys.stdout)

    # Find Pdf's inside a Dir of Dir's downloaded from Chase Bank

    filepaths = []
    for step in os.walk('.'):
        (dirpath, dirnames, filenames,) = step

        dirnames.sort()
        filenames.sort()

        for filename in filenames:
            if filename.endswith('.pdf'):
                filepath = os.path.join(dirpath, filename)

                filepaths.append(filepath)

    # Collect Transactions from each Pdf

    main.sortables = []
    for filepath in filepaths:
        dirpath = os.path.dirname(filepath)

        chars = plain_ascii_str(open(filepath, 'rb').read())
        lines = chars.split('\n')  # more like 'vi' than chars.splitlines()

        main.trace.filepath = filepath
        main.trace.lines = lines

        for pdf_tag in ('CREDIT CARD', 'TOTAL CHECKING',):
            if pdf_tag in dirpath:  # wart: else trash silently
               pdf_parse(pdf_tag, filepath=filepath, lines=lines)

    # Sort Transactions

    sortables = list(main.sortables)
    sortables.sort()

    rows = [s[-1] for s in sortables]

    # Export Transactions, after one Header Row

    header = ('', 'Yyyy-mm-dd', 'Amount', 'Merchant', 'Notes',)
    csv_writer.writerow(header)
    csv_writer.writerows(rows)

    # Count the cost of run time

    when_quit = dt.datetime.now()
    print('Chase Py ran inside', when_quit - when_launched)


def pdf_parse(pdf_tag, filepath, lines):
    """Convert from Pdf Printout of Credit Card Statement from Chase Bank"""

    # Work up guesses from the Pdf filename

    tail = filepath[filepath.index(pdf_tag):]
    pattern = r'^{} \([.][.][.]([0-9]+)\)/([0-9]+)-statements-([0-9]+)-.pdf$'.format(pdf_tag)
    matched = re.match(pattern, string=tail)

    str_account = matched.group(1)
    assert matched.group(1) == matched.group(3)

    str_yyyymmdd = matched.group(2)
    ymd = dt.datetime.strptime(str_yyyymmdd, r'%Y%m%d')

    # Guess the Year of each Month of a Transaction

    year_by_month = dict()

    ym1 = ymd
    for _ in range(3):  # >= 3 to let February can show up in April

        year_by_month[ym1.month] = ym1.year

        ym1 = dt.datetime(year=ym1.year, month=ym1.month, day=1)
        ym1 = (ym1 - dt.timedelta(days=28))  # wart: '28' means 1 month ago

    # Publish guesses

    pdf_parse.str_account = str_account
    pdf_parse.year_by_month = year_by_month

    # Divide the Pdf into Streams

    whole = LineTaker(lines)
    assert whole

    if pdf_tag == 'TOTAL CHECKING':
        whole.trash_lines_beyond_regex(r'^\[\( CHASE SAVINGS\)\] TJ$')
        whole.skip_lines_till_regex(r'^\(TRANSACTION DETAIL\)Tj$')
            # to skip hits of LEADING_TJ_REGEX in rows of Check Number, Date Paid, Amount

    while whole:
        whole.skip_lines_till_transaction()
        if whole:
            whole.collect_transaction_lines(pdf_tag)


class LineTaker(object):
    """Walk thru the lines of a file"""

    def __init__(self, lines):

        self.lines = lines
        self.len_takeable_lines = len(lines)

    def __len__(self):

        len_ = len(self.lines)
        return len_

    def lineno(self):
        """Calculate line number of next untaken line"""

        lineno = (self.len_takeable_lines - len(self.lines) + 1)
        return lineno

    def skip_lines_till_transaction(self):
        """Skip lines up to next transaction, else thru Eof"""

        len_skippable = len(self.lines)
        self.skip_lines_till_regex(LEADING_TJ_REGEX)
        len_skipped = (len_skippable - len(self.lines))

        max_skipped = 1000  # seen 807, 319, 254, 150, 106, 85
        if len(self.lines) == self.len_takeable_lines:
            max_skipped = 1500  # seen 807 up front
        elif not self.lines:
            max_skipped = 4500  # seen 3090 out back

        assert len_skipped <= max_skipped

    def skip_lines_till_regex(self, regex):
        """Skip lines up to next match of regex, else thru Eof"""

        lines = self.lines
        while lines and not re.match(regex, string=lines[0]):
            lines = lines[1:]

        self.lines = lines

    def trash_lines_beyond_regex(self, regex):
        """Trash lines beyond next match of regex"""

        lines = self.lines
        while lines and not re.match(regex, string=lines[0]):
            lines = lines[1:]

        assert lines
        self.lines = self.lines[:-len(lines)]

    def collect_transaction_lines(self, pdf_tag):
        if pdf_tag == 'CREDIT CARD':
            self.collect_credit_card_lines()
        else:
            assert pdf_tag == 'TOTAL CHECKING'
            self.collect_total_checking_lines()

    def collect_total_checking_lines(self):
        """Take the lines of a Total Checking  Transaction, and collect them"""

        lines = self.lines
        assert re.match(LEADING_TJ_REGEX, string=lines[0])

        # Require Tj-Tm pairs

        len_transaction_lines = 10
        copies = list(lines[:len_transaction_lines])

        """
        if len(copies) < len_transaction_lines:  # wart: lines from Savings land a lil above it
            if copies[2] == '(Interest Payment)Tj':
                self.lines = []
                return
        """

        regexes = textwrap.dedent(r"""
            ^\(ATM Check Deposit
            ^\(Card Purchase Return
            ^\(Card Purchase W/Cash
            ^\(Deposit
            ^\(Interest Payment
            ^\(Online Transfer From Chk
            ^\(Online Transfer From Sav
            ^\(Paypal
            ^\(Purchase Return
            ^\(Transfer From Chk
            ^\([A-Za-z0-9_ ]*Dir Dep
            ^\([A-Za-z0-9_ ]*Payment
        """).strip().splitlines()

        for regex in regexes:
            if re.match(regex, string=copies[2]):  # wart: amount lost
                len_transaction_lines = 6
                self.lines = self.lines[len_transaction_lines:]
                return

        if copies[6] == '(-)Tj':  # wart: Card Purchase just sometimes adds a line
            for index in range(4, 10):
                copies[index] = lines[2 + index]
            len_transaction_lines += 2

        for index in range(1, len(copies), 2):
            assert re.match(PAIRED_TM_REGEX, string=copies[index])

        date_of = pick_from_tj(copies[0])
        merchant = pick_from_tj(copies[2])
        minus = pick_from_tj(copies[4])
        amount = pick_from_tj(copies[6])  # in the currency local to my bank
        balance = pick_from_tj(copies[8])

        assert '"' not in merchant
        assert minus == '-'
        assert re.match(r'^[0-9.,]+$', string=amount)
        assert re.match(r'^[0-9.,]+$', string=balance)

        # Guess Year-Month-Day from Chase "Date of"  # wart: great pile of copy-edited sourcelines

        splits = date_of.split('/')
        assert len(splits) == 2
        month = int(splits[0])
        day = int(splits[1])

        year = pdf_parse.year_by_month[month]

        ymd = '{}-{:02}-{:02}'.format(year, month, day)
        assert len(ymd) == len('1999-12-31')

        # Work up some notes of details

        notes = []

        notes.append('{}-account'.format(pdf_parse.str_account))
            # WART: difficult to write leading zeroes into Csv

        matched = re.match(r'^(.*[0-9][0-9]/[0-9][0-9] )(.*)$', string=merchant)
        if not matched:
            split_merchant = ' '.join(merchant.split())
        else:
            split_note = matched.group(1).strip()
            split_merchant = matched.group(2).strip()

            matched = re.match(r'^(.*) Card( [0-9]+)?$', string=split_merchant)
            if not matched:
                notes.append(split_note)
            else:
                split_merchant = matched.group(1).strip()
                split_note += ' Card'
                if matched.group(2):
                    split_note += matched.group(2).strip()
                split_note = split_note.strip()

            for regex in (r'^(Online Payment [0-9]+) ', r'^(Online Transfer) '):
                matched = re.match(regex, string=split_merchant)
                if matched:
                    split_merchant = split_merchant[len(matched.group(1)):].strip()
                    split_note += (' ' + matched.group(1))

            for regex in (r'( Transaction#: [0-9]+)$',):
                matched = re.search(regex, string=split_merchant)  # search to end, not match front
                if matched:
                    split_merchant = split_merchant[:-len(matched.group(1))].strip()
                    split_note += (' ' + matched.group(1))

            notes.append(split_note.strip())

        str_notes = ', '.join(notes)

        # Collect this row

        key = (ymd, len(main.sortables),)  # wart: cleverly stable sort
        row = ('', ymd, amount, split_merchant, str_notes,)

        sortable = (key, row,)
        main.sortables.append(sortable)

        # Take the lines collected

        self.lines = self.lines[len_transaction_lines:]

    def collect_credit_card_lines(self):
        """Take the lines of a Credit Card Transaction, and collect them"""

        lines = self.lines
        assert re.match(LEADING_TJ_REGEX, string=lines[0])

        # Require Tj-Tm pairs

        len_transaction_lines = 8
        copies = list(lines[:len_transaction_lines])

        if (copies[4], copies[6],) == ('[( )] TJ', '(&)Tj'):
            assert re.match(PAIRED_TM_REGEX, string=copies[5])
            assert re.match(PAIRED_TM_REGEX, string=copies[7])

            copies[4] = lines[4 + 4]
            copies[5] = lines[4 + 5]
            copies[6] = lines[4 + 6]
            copies[7] = lines[4 + 7]

            len_transaction_lines += 4  # wart: who knows how often

        if copies[7].endswith(' k'):

            copies[7] = lines[len_transaction_lines]

            len_transaction_lines += 1  # wart: who knows how often

        assert re.match(PAIRED_TM_REGEX, string=copies[1])
        assert re.match(PAIRED_TM_REGEX, string=copies[3])
        assert re.match(PAIRED_TM_REGEX, string=copies[5])
        assert re.match(PAIRED_TM_REGEX, string=copies[7])

        # Extract Date-Of, Amount, Merchant

        date_of = pick_from_tj(copies[0])
        transaction = pick_from_tj(copies[2])
        merchant = pick_from_tj(copies[4])
        amount = pick_from_tj(copies[6])  # in the currency local to my bank

        merchant = merchant.strip()
        assert re.match(r'^[-]?[0-9,]*[.][0-9]+$', string=amount)

        assert transaction == ' '
        assert '"' not in merchant

        # Guess Year-Month-Day from Chase "Date of"

        splits = date_of.split('/')
        assert len(splits) == 2
        month = int(splits[0])
        day = int(splits[1])

        year = pdf_parse.year_by_month[month]

        ymd = '{}-{:02}-{:02}'.format(year, month, day)
        assert len(ymd) == len('1999-12-31')

        # Work up some notes of details

        notes = []

        notes.append('{}-account'.format(pdf_parse.str_account))
            # WART: difficult to write leading zeroes into Csv

        str_notes = ', '.join(notes)

        # Collect this row

        key = (ymd, len(main.sortables),)  # wart: cleverly stable sort
        row = ('', ymd, amount, merchant, str_notes,)

        sortable = (key, row,)
        main.sortables.append(sortable)

        # Take the lines collected

        self.lines = self.lines[len_transaction_lines:]


def pick_from_tj(line):
    """Extract from the middle of '(...)Tj' or from '[(...)] TJ"""

    matched = re.match(r'^\((.*)\)Tj$', string=line)
    matched = matched or re.match(r'^\[\((.*)\)\] TJ$', string=line)

    stripped = matched.group(1)
    return stripped


def plain_ascii_str(bytes_):
    """Force fit arbitrary bytes into one or more US ASCII log lines of only printable text"""

    s = bytes_
    s = ascii_str(s)
    s = re.sub(r'[^\t\n\r -~]', repl='?', string=s)
    s = s.expandtabs()  # tabsize=8
    s = s.replace('\r\n', '\n')  # don't strip 1 trailing '\n' like '\n'.join(s.splitlines()) would
    s = s.replace('\r', '\n')

    return s


def ascii_str(bytes_):
    """Convert arbitrary bytes to a 'str' (never Python 2 'unicode') of US-Ascii chars"""

    s = bytes_  # such as b'\xC0\x80' to inject decoding error
    s = s.decode('ascii', errors='replace')  # Py 3 'str' from 'bytes', Py 2 'unicode' from 'bytes'
    s = s.replace(u'\uFFFD', '?')  # Ascii '?' in place of each Unicode Replacement Char
    s = str(s)  # Py 3 'str' from 'str', or Py 2 'str' from 'unicode'

    return s

# TODO: Add notes of parsing difficulties to transactions
# TODO: Emit local price before exchange rate applied
