# -*- coding: utf-8 -*-

import time, datetime
from odoo import api, fields, models

def get_previous_date(year, month):
    """Generator to continuously return the previous month and year."""
    while True:
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        yield datetime.date(year, month, 1)

def last_day_of_month(date):
    if date.month == 12:
        return date.replace(day=31)
    return date.replace(month=date.month+1, day=1) - datetime.timedelta(days=1)
