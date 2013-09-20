#This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
#at the top level of this repository contains the full copyright notices and
#license terms.

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import Eval
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['PrintTaxesByInvoiceAndPeriodStart', 'PrintTaxesByInvoiceAndPeriod',
    'TaxesByInvoiceReport', 'TaxesByInvoiceAndPeriodReport']


class PrintTaxesByInvoiceAndPeriodStart(ModelView):
    'Print Taxes by Invoice and Period'
    __name__ = 'account_jasper_reports.print_taxes_by_invoice.start'

    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
            required=True, on_change=['fiscalyear'])
    periods = fields.Many2Many('account.period', None, None, 'Periods',
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ], depends=['fiscalyear'])
    report_type = fields.Selection([('taxes-by-invoice', 'Taxes by Invoice')],
        'Report', required=True)
    partner_type = fields.Selection([
            ('customers', 'Customers'),
            ('suppliers', 'Suppliers'),
            ], 'Partner Type', required=True)
    grouping = fields.Selection([
            ('base_tax_code', 'Base Tax Code'),
            ('invoice', 'Invoice'),
            ], 'Grouping', required=True)
    totals_only = fields.Boolean('Totals Only')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    output_type = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Type', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_report_type():
        return 'taxes-by-invoice'

    @staticmethod
    def default_partner_type():
        return 'customers'

    @staticmethod
    def default_grouping():
        return 'base_tax_code'

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_output_type():
        return 'pdf'

    def on_change_fiscalyear(self):
        return {'periods': None, }


class PrintTaxesByInvoiceAndPeriod(Wizard):
    'Print TaxesByInvoiceAndPeriod'
    __name__ = 'account_jasper_reports.print_taxes_by_invoice'
    start = StateView('account_jasper_reports.print_taxes_by_invoice.start',
        'account_jasper_reports.print_taxes_by_invoice_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('account_jasper_reports.report_taxes_by_invoice')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'fiscalyear': self.start.fiscalyear.id,
            'periods': [x.id for x in self.start.periods],
            'parties': [x.id for x in self.start.parties],
            'output_type': self.start.output_type,
            'report_type': self.start.report_type,
            'partner_type': self.start.partner_type,
            'totals_only': self.start.totals_only,
            'grouping': self.start.grouping,
            }
        if data['grouping'] == 'invoice':
            state_action = StateAction('account_jasper_reports.'
                'report_taxes_by_invoice_and_period')
            action = state_action.get_action()
        return action, data

    def transition_print_(self):
        return 'end'

    def default_start(self, fields):
        Party = Pool().get('party.party')
        party_ids = []
        if Transaction().context.get('model') == 'party.party':
            for party in Party.browse(Transaction().context.get('active_ids')):
                party_ids.append(party.id)
        return {
            'parties': party_ids,
            }


class TaxesByInvoiceReport(JasperReport):
    __name__ = 'account_jasper_reports.taxes_by_invoice'

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        Period = pool.get('account.period')
        Party = pool.get('party.party')
        AccountInvoiceTax = pool.get('account.invoice.tax')
        fiscalyear = FiscalYear(data['fiscalyear'])
        periods = Period.browse(data.get('periods', []))
        parties = Party.browse(data.get('parties', []))

        if parties:
            js = Party.search([('id', 'in', [x.id for x in parties])])
            parties_subtitle = []
            for x in js:
                if len(parties_subtitle) > 4:
                    parties_subtitle.append('...')
                    break
                parties_subtitle.append(x.name)
            parties_subtitle = '; '.join(parties_subtitle)
        else:
            parties_subtitle = ''

        parameters = {}
        parameters['fiscal_year'] = fiscalyear.rec_name
        parameters['parties'] = parties_subtitle
        parameters['TOTALS_ONLY'] = data['totals_only'] and True or False

        domain = []

        if data['partner_type'] == 'customers':
            domain += [('invoice.type', 'in',
                    ('out_invoice', 'out_credit_note'))]
        else:
            domain += [('invoice.type', 'in',
                    ('in_invoice', 'in_credit_note'))]

        if periods:
            domain += [('invoice.move.period', 'in', periods)]

        if parties:
            domain += [('invoice.party', 'in', parties)],

        report_ids = [x.id for x in AccountInvoiceTax.search(domain)]
        return super(TaxesByInvoiceReport, cls).execute(report_ids, {
                'name': cls.__name__,
                'parameters': parameters,
                'output_format': data['output_type'],
                })


class TaxesByInvoiceAndPeriodReport(TaxesByInvoiceReport):
    __name__ = 'account_jasper_reports.taxes_by_invoice_and_period'