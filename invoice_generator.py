import time
import requests
import json
import pytz
import locale
import csv

from datetime import datetime, date


class InvoiceGenerator:
    """API Object for Invoice-Generator tool - https://invoice-generator.com/"""

    URL = "https://invoice-generator.com"
    DATE_FORMAT = "%d %b %Y"
    LOCALE = "en_US.utf8"
    TIMEZONE = "UTC"
    # Below are the default template parameters that can be changed (see https://github.com/Invoiced/invoice-generator-api/)
    TEMPLATE_PARAMETERS = [
        "header",
        "to_title",
        "ship_to_title",
        "invoice_number_title",
        "date_title",
        "payment_terms_title",
        "due_date_title",
        "purchase_order_title",
        "quantity_header",
        "item_header",
        "unit_cost_header",
        "amount_header",
        "subtotal_title",
        "discounts_title",
        "tax_title",
        "shipping_title",
        "total_title",
        "amount_paid_title",
        "balance_title",
        "terms_title",
        "notes_title",
    ]

    def __init__(
        self,
        sender,
        to,
        logo=None,
        ship_to=None,
        number=None,
        payments_terms=None,
        due_date=None,
        notes=None,
        terms=None,
        currency="USD",
        date=datetime.now(tz=pytz.timezone(TIMEZONE)),
        discounts=0,
        tax=0,
        shipping=0,
        amount_paid=0,
    ):
        """Object constructor"""
        self.logo = logo
        self.sender = sender
        self.to = to
        self.ship_to = ship_to
        self.number = number
        self.currency = currency
        self.custom_fields = []
        self.date = date
        self.payment_terms = payments_terms
        self.due_date = due_date
        self.items = []
        self.fields = {"tax": "%", "discounts": False, "shipping": False}
        self.discounts = discounts
        self.tax = tax
        self.shipping = shipping
        self.amount_paid = amount_paid
        self.notes = notes
        self.terms = terms
        self.template = {}

    def _to_json(self):
        """
        Parsing the object as JSON string
        Please note we need also to replace the key sender to from, as per expected in the API but incompatible with from keyword inherent to Python
        We are formatting here the correct dates
        We are also resetting the two list of Objects items and custom_fields so that it can be JSON serializable
        Finally, we are handling template customization with its dict
        """
        locale.setlocale(locale.LC_ALL, InvoiceGenerator.LOCALE)
        object_dict = self.__dict__
        object_dict["from"] = object_dict.get("sender")
        object_dict["date"] = self.date.strftime(InvoiceGenerator.DATE_FORMAT)
        if object_dict["due_date"] is not None:
            object_dict["due_date"] = self.due_date.strftime(
                InvoiceGenerator.DATE_FORMAT
            )
        object_dict.pop("sender")
        for index, item in enumerate(object_dict["items"]):
            object_dict["items"][index] = item.__dict__
        for index, custom_field in enumerate(object_dict["custom_fields"]):
            object_dict["custom_fields"][index] = custom_field.__dict__
        for template_parameter, value in self.template.items():
            object_dict[template_parameter] = value
        object_dict.pop("template")
        return json.dumps(object_dict)

    def add_custom_field(self, name=None, value=None):
        """Add a custom field to the invoice"""
        self.custom_fields.append(CustomField(name=name, value=value))

    def add_item(self, name=None, quantity=0, unit_cost=0.0, description=None):
        """Add item to the invoice"""
        self.items.append(
            Item(
                name=name,
                quantity=quantity,
                unit_cost=unit_cost,
                description=description,
            )
        )

    def download(self, file_path):
        """Directly send the request and store the file on path"""
        json_string = self._to_json()
        response = requests.post(
            InvoiceGenerator.URL,
            json=json.loads(json_string),
            stream=True,
            headers={"Accept-Language": InvoiceGenerator.LOCALE},
        )
        if response.status_code == 200:
            open(file_path, "wb").write(response.content)
        else:
            raise Exception(
                f"Invoice download request returned the following message:{response.json()} Response code = {response.status_code} "
            )

    def set_template_text(self, template_parameter, value):
        """If you want to change a default value for customising your invoice template, call this method"""
        if template_parameter in InvoiceGenerator.TEMPLATE_PARAMETERS:
            self.template[template_parameter] = value
        else:
            raise ValueError(
                "The parameter {} is not a valid template parameter. See docs.".format(
                    template_parameter
                )
            )

    def toggle_subtotal(self, tax="%", discounts=False, shipping=False):
        """Toggle lines of subtotal"""
        self.fields = {"tax": tax, "discounts": discounts, "shipping": shipping}


class Item:
    """Item object for an invoice"""

    def __init__(self, name, quantity, unit_cost, description=""):
        """Object constructor"""
        self.name = name
        self.quantity = quantity
        self.unit_cost = unit_cost
        self.description = description


class CustomField:
    """Custom Field object for an invoice"""

    def __init__(self, name, value):
        """Object constructor"""
        self.name = name
        self.value = value


date_key = "Date (UTC)"
description = "Description"
amount = "Amount"


def clean(record):
    record[date_key] = datetime.strptime(record[date_key], "%m-%d-%Y").date()
    record[amount] = float(record[amount])
    return record


if __name__ == "__main__":
    with open("transactions.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        records = map(clean, reader)
        for i, row in enumerate(records):
            if row[amount] < 0:
                continue
            invoice = InvoiceGenerator(
                "EA2 Consulting", to=row[description], date=row[date_key]
            )
            invoice.add_item(
                name="Consultative services", quantity=1, unit_cost=row[amount]
            )
            invoice.download(file_path=f"invoices/{row[date_key]}.pdf")
            time.sleep(1)
