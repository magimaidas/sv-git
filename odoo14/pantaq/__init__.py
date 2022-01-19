# -*- coding: utf-8 -*-

from . import wizard
from . import controllers
from . import models


# Remove group from res.group once uninstalled
def delete_group(cr, registry):
    query = "delete from res_groups where name ilike '%Show Customer Quotation menu for Executives%'"
    cr.execute(query)