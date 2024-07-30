import frappe
from frappe.utils import cint, cstr, flt, get_formatted_email, today
from datetime import datetime
from datetime import timedelta
from datetime import date
from frappe import _
import json
from frappe.utils.user import get_users_with_role

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


    credit_amount_data = get_credit_amount(self.customer,self.category)
    bypass_credit_limit = frappe.db.get_value("Customer Credit Limit Custom",{'parent':self.customer,'category':self.category},'bypass_credit_limit_check_at_sales_order')
    if bypass_credit_limit == 0:
        if credit_amount_data and flt(credit_amount_data['customer_outstanding_amount']) > flt(credit_amount_data['customer_credit_limit']):
            frappe.msgprint("Credit Limit Amount Exceeds For Customer-"+self.customer+ self.category + " Limit)")

            # If not authorized person raise exception
            credit_controller_role = frappe.db.get_single_value("Accounts Settings", "credit_controller")
            if not credit_controller_role or credit_controller_role not in frappe.get_roles():
                # form a list of emails for the credit controller users
                credit_controller_users = get_users_with_role(credit_controller_role or "Sales Master Manager")

                # form a list of emails and names to show to the user
                credit_controller_users_formatted = [
                    get_formatted_email(user).replace("<", "(").replace(">", ")")
                    for user in credit_controller_users
                ]
                if not credit_controller_users_formatted:
                    frappe.throw(
                        _("Please contact your administrator to extend the credit limit for {0}.").format(self.customer)
                    )

                message = """Please contact any of the following users to extend the credit Limit for {0}:
                    <br><br><ul><li>{1}</li></ul>""".format(
                    self.customer, "<li>".join(credit_controller_users_formatted)
                )

                # if the current user does not have permissions to override credit limit,
                # prompt them to send out an email to the controller users
                frappe.msgprint(
                    message,
                    title="Notify",
                    raise_exception=1,
                    primary_action={
                        "label": "Send Email",
                        "server_action": "credit_days_customization.credit_days_customization.override_function.sales_order.send_emails_credit_amount",
                        "args": {
                            "customer": self.customer,
                            "customer_pending_payment_amount": credit_amount_data['customer_outstanding_amount'],
                            "credit_limit_amount": credit_amount_data['customer_credit_limit'],
                            "credit_controller_users_list": credit_controller_users,
                        },
                    },
                )


    # Credit Limit On Days
    credit_days_data = get_credit_days(self.customer,self.transaction_date,self.category)
    # frappe.msgprint(str(credit_days_data))
    bypass_credit_limit = frappe.db.get_value("Customer Credit Limit Custom",{'parent':self.customer,'category':self.category},'bypass_credit_limit_check_at_sales_order')
    if bypass_credit_limit == 0:
        if credit_days_data and (int(credit_days_data['pending_invoice_date']) > int(credit_days_data['customer_credit_days'])):
            frappe.msgprint("Credit Limit Days Exceeded for Customer - " + self.customer + " (" + credit_days_data['pending_invoice_date'] + "/" + credit_days_data['customer_credit_days'] + " Days)")
            
            # If not authorized person raise exception
            credit_controller_role = frappe.db.get_single_value("Accounts Settings", "credit_controller")
            if not credit_controller_role or credit_controller_role not in frappe.get_roles():
                # form a list of emails for the credit controller users
                credit_controller_users = get_users_with_role(credit_controller_role or "Sales Master Manager")

                # form a list of emails and names to show to the user
                credit_controller_users_formatted = [
                    get_formatted_email(user).replace("<", "(").replace(">", ")")
                    for user in credit_controller_users
                ]
                if not credit_controller_users_formatted:
                    frappe.throw(
                        _("Please contact your administrator to extend the credit days for {0}.").format(self.customer)
                    )

                message = """Please contact any of the following users to extend the credit days for {0}:
                    <br><br><ul><li>{1}</li></ul>""".format(
                    self.customer, "<li>".join(credit_controller_users_formatted)
                )

                # if the current user does not have permissions to override credit limit,
                # prompt them to send out an email to the controller users
                frappe.msgprint(
                    message,
                    title="Notify",
                    raise_exception=1,
                    primary_action={
                        "label": "Send Email",
                        "server_action": "credit_days_customization.credit_days_customization.override_function.sales_order.send_emails",
                        "args": {
                            "customer": self.customer,
                            "customer_pending_payment_days": int(credit_days_data['pending_invoice_date']),
                            "credit_days": int(credit_days_data['customer_credit_days']),
                            "credit_controller_users_list": credit_controller_users,
                        },
                    },
                )








@frappe.whitelist()
def send_emails(args):
    args = json.loads(args)
    subject = _("Credit days reached for customer {0}").format(args.get("customer"))
    message = _("Credit days has been crossed for customer {0} ({1}/{2})").format(
        args.get("customer"), args.get("customer_pending_payment_days"), args.get("credit_days")
    )
    frappe.sendmail(
        recipients=args.get("credit_controller_users_list"), subject=subject, message=message
    )
#For Send mail for customer credit limit
@frappe.whitelist()
def send_emails_credit_amount(args):
    args = json.loads(args)
    subject = _("Credit limit reached for customer {0}").format(args.get("customer"))
    message = _("Credit limit has been crossed for customer {0} ({1}/{2})").format(
        args.get("customer"), args.get("customer_pending_payment_amount"), args.get("credit_limit_amount")
    )
    frappe.sendmail(
        recipients=args.get("credit_controller_users_list"), subject=subject, message=message
    )


@frappe.whitelist()
def get_credit_days(customer,date,category):
    credit_days_customer = frappe.db.get_value("Customer Credit Limit Custom",{'parent': customer, 'parenttype': 'Customer','category':category}, 'credit_days')

    if credit_days_customer:
        days_from_last_invoice_raw = frappe.db.sql("select DATEDIFF(CURDATE(),si.posting_date) as date,category from `tabSales Invoice` si where si.customer = %s and si.outstanding_amount > 0 and si.category = %s order by si.posting_date asc limit 1 ", (customer,category), as_dict =1)
        if not days_from_last_invoice_raw:
            days_from_last_invoice = 0
        else:
            days_from_last_invoice = str(days_from_last_invoice_raw[0].date)

        return {            
            "pending_invoice_date": str(days_from_last_invoice),
            "customer_credit_days": str(credit_days_customer)
        }

@frappe.whitelist()
def get_credit_amount(customer,category):
    credit_amount_customer = frappe.db.get_value("Customer Credit Limit Custom",{'parent':customer,'parenttype': 'Customer','category':category},'credit_limit_amount')
    
    if credit_amount_customer:
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

            """,(customer,category),as_dict = 1)
        
        if not outstanding_value:
            customer_outstanding_value = 0.00    
        else:
            customer_outstanding_value = str(outstanding_value[0].outstanding_amount)    

        return {
            "customer_outstanding_amount":flt(customer_outstanding_value),
            "customer_credit_limit":flt(credit_amount_customer)
            }
