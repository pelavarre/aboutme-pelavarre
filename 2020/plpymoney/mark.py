#!/usr/bin/env python3

r"""
Divide transactions into categories, by marking them with labels
"""


import collections
import csv
import datetime as dt
import re


def main():
    """Divide transactions into categories, by marking them with labels"""

    when_launched = dt.datetime.now()

    # Map merchants to categories

    category_by_merchant = dict()

    csv_reader = csv.reader(open('category-by-merchant-csv.csv'))
    header_row = next(csv_reader)
    assert header_row == ['', 'Category', 'Merchant']

    for row in csv_reader:
        (_, category, merchant,) = row
        category_by_merchant[merchant] = category

    # Join categories to transactions

    csv_writer = csv.writer(open('chase-mark-csv.csv', 'w'))

    csv_reader = csv.reader(open('chase-export-csv.csv'))
    header_row = next(csv_reader)
    assert header_row == ['', 'Yyyy-mm-dd', 'Amount', 'Merchant', 'Notes']

    csv_rows = list(csv_reader)  # discover empty before writing header out

    marked_rows = []
    more_merchants = set()
    if csv_rows:

        marked_header_row = list(header_row)
        marked_header_row[3:3] = ['Category']
        csv_writer.writerow(marked_header_row)

        sortables = []
        for row in csv_rows:
            (_, ymd, amount, merchant, notes,) = row

            category = category_by_merchant.get(merchant)
            if not category:
                more_merchants.add(merchant)

            sort_key = (category, len(sortables),)
            marked_row = ('', ymd, amount, category, merchant, notes,)
            sortable = (sort_key, marked_row,)

            sortables.append(sortable)

        sortables.sort()
        for sortable in sortables:
            (_, marked_row) = sortable
            csv_writer.writerow(marked_row)

            marked_rows.append(marked_row)

    # Sum amounts by category

    csv_writer = csv.writer(open('sum-by-category-csv.csv', 'w'))
    csv_writer.writerow('Amount Category'.split())

    cents_by_category = collections.defaultdict(int)
    for marked_row in marked_rows:
        (_, _, amount, category, _, _,) = marked_row

        assert re.match(r'^[-]?[0-9,]*[.][0-9][0-9]$', string=amount)
        if not amount.startswith('-'):
            cents = int(amount.replace(',', '').replace('.', ''))
            cents_by_category[category] += cents

    sortables = []
    for category in sorted(cents_by_category.keys()):
        cents = cents_by_category[category]
        sortable = (cents, category,)
        sortables.append(sortable)

    sortables.sort(reverse=True)

    empty_row = ()
    csv_writer.writerow(empty_row)
    csv_writer.writerow(empty_row)

    summed_cents = 0
    for (cents, category,) in sortables:
        if category not in 'Check Money'.split():
            summed_cents += cents
        row = (None, cents / 1e0 / 100, category,)
        csv_writer.writerow(row)
        if category == 'Check':
            csv_writer.writerow(empty_row)

    csv_writer.writerow(empty_row)
    row = (None, summed_cents / 1e0 / 100, 'apart from Checks & Money',)
    csv_writer.writerow(row)

    csv_writer.writerow(empty_row)
    csv_writer.writerow(empty_row)

    # List the uncategorized merchants

    csv_writer = csv.writer(open('more-merchants-csv.csv', 'w'))

    if more_merchants:
        csv_writer.writerow(['', 'Category', 'Merchant'])

        category = None
        for merchant in sorted(more_merchants):
            row = ('', category, merchant,)
            csv_writer.writerow(row)

    # Count the cost of run time

    when_quit = dt.datetime.now()
    print('Mark Py ran inside', when_quit - when_launched)
