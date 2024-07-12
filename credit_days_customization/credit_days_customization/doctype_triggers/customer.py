import frappe
from frappe import _

def validate(self,method):
    category_record = []
    for limit in self.custom_credit_limit:
        if limit.category in category_record:
            frappe.throw( _("Credit limit is already defined for the Category {0}").format(limit.category, self.name))
        else:
            category_record.append(limit.category)