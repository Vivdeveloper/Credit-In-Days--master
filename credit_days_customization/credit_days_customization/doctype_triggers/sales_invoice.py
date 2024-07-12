import frappe
from frappe.utils import cint, cstr, flt, get_formatted_email, today
from datetime import datetime
from datetime import timedelta
from datetime import date

def on_submit(self,method):
    customer_allocation_rate = frappe.db.get_value("Customer",self.customer,'customer_amount_allocation')
    if customer_allocation_rate != 0:
        if customer_allocation_rate < self.rounded_total:
            frappe.throw("Customer Allocation Amount Exceeds!")

    # Validation For Customer Credit Limit On Amount
    credit_amount_customer = frappe.db.get_value("Customer Credit Limit Custom",{'category':self.category,'parent':self.customer},'credit_limit_amount')
    
    if credit_amount_customer and not self.is_return:
        outstanding_value = frappe.db.sql("""
                select
                sum(si.outstanding_amount) as outstanding_amount
                from
                `tabSales Invoice` si
                where
                si.status != "Paid" 
                and
                si.docstatus = 1
                and
                si.customer = %s and si.outstanding_amount > 0 and si.category = %s

                """,(self.customer,self.category),as_dict = 1)  

        if outstanding_value[0].outstanding_amount > credit_amount_customer:
            frappe.throw("Customer Credit Amount limit Exceeds For This Category")
    else:
        pass        


    # Validation For Customer Credit Limit On Days
    credit_days_customer = frappe.db.get_value("Customer Credit Limit Custom",{'parent': self.customer,'category':self.category}, 'credit_days')
    
    if credit_days_customer:
        credit_days_value = frappe.db.sql("select DATEDIFF(CURDATE(),si.posting_date) as date,category from `tabSales Invoice` si where si.customer = %s and si.outstanding_amount > 0 and si.category = %s order by si.posting_date asc limit 1", (self.customer,self.category), as_dict =1)
        
        if credit_days_value[0].date > credit_days_customer:
            frappe.throw("Customer Credit Days limit Exceeds For This Category")
    else:
        pass        

