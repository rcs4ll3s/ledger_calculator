from decimal import Decimal
from datetime import datetime, timedelta
from typing import Iterable, Tuple


class LedgerCalculator:
    def __init__(
        self,
        events: Iterable,
        end_date: str,
        interest_rate: Decimal = Decimal('0.00035'),
    ) -> None:
        self.events = events
        self.end_date = end_date
        self.interest_rate = interest_rate
        self.overall_advance_balance = Decimal(0)
        self.overall_interest_payable_balance = Decimal(0)
        self.overall_interest_paid = Decimal(0)
        self.overall_payments_for_future = Decimal(0)
        self.last_interest_date_calculated = None
        self.advances = []
        self.event_handlers = {
            'advance': self._advance_event_handler,
            'payment': self._payment_event_handler,
        }

    def calculate_balances(self) -> None:
        for event in self.events:
            self.event_handlers[event['type']](event)
        end_interest_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
        end_interest_date = str(end_interest_date + timedelta(days=1))
        self._calculate_interest_to_pay(interest_date=end_interest_date)

    def _advance_event_handler(self, event) -> None:
        self._calculate_interest_to_pay(interest_date=event['date_created'])
        event_amount = Decimal(event['amount'])
        current_balance_for_this_advance = self._pay_with_account_balance(
            event_amount
        )
        self.advances.append(
            {
                "id": event['id'],
                "date": event['date_created'],
                "initial_amount": event_amount,
                "current_balance": current_balance_for_this_advance,
            }
        )
        self.overall_advance_balance += current_balance_for_this_advance

    def _payment_event_handler(self, event) -> None:
        self._calculate_interest_to_pay(interest_date=event['date_created'])
        self._pay(payment_amount=Decimal(event['amount']))

    def _calculate_interest_to_pay(self, interest_date: str = None) -> None:
        if not self.last_interest_date_calculated:
            self.last_interest_date_calculated = datetime.strptime(
                interest_date, '%Y-%m-%d'
            )
            return

        interest_date = datetime.strptime(interest_date, '%Y-%m-%d')
        delta = interest_date - self.last_interest_date_calculated
        total_days = delta.days

        self.overall_interest_payable_balance += (
            self.overall_advance_balance * self.interest_rate * total_days
        )
        self.last_interest_date_calculated = interest_date

    def _pay_with_account_balance(self, advanced_amount: Decimal) -> Decimal:
        # Check if there is a balance in the account, to deduct this new loan
        # and return the new amount after the operation
        if self._has_account_balance():
            (
                advanced_amount,
                self.overall_payments_for_future,
            ) = self._subtract_smaller_from_larger(
                advanced_amount, self.overall_payments_for_future
            )
        return advanced_amount

    def _has_account_balance(self) -> bool:
        return bool(self.overall_payments_for_future)

    def _pay(self, payment_amount: Decimal) -> None:
        # First, to reduce the "*interest payable balance*" for the customer
        if self._has_interest_balance_to_pay():
            payment_amount = self._pay_interest(payment_amount)
            if not payment_amount:
                return

        # Second, any remaining amount of the repayment is applied to reduce the "advance balance" of the *oldest* active
        # advance, and if there is any remaining amount it reduces the amount of the following (second oldest) advance, and so
        # on
        if self._has_advanced_balances_to_pay():
            payment_amount = self._pay_advanced_balances(payment_amount)
            if not payment_amount:
                return

        # Finally - after *all* advances have been repaid - if there is still some amount of the repayment available, the remaining
        # amount of the repayment should be credited towards to immediately paying down future advances
        self.overall_payments_for_future += payment_amount

    def _has_interest_balance_to_pay(self) -> bool:
        return bool(self.overall_interest_payable_balance)

    def _pay_interest(self, payment_amount: Decimal) -> Decimal:
        if payment_amount >= self.overall_interest_payable_balance:
            interest_paid = self.overall_interest_payable_balance
            payment_amount -= interest_paid
            self.overall_interest_payable_balance = Decimal(0)
        else:
            interest_paid = payment_amount
            self.overall_interest_payable_balance -= interest_paid
            payment_amount = Decimal(0)
        self.overall_interest_paid += interest_paid
        return payment_amount

    def _has_advanced_balances_to_pay(self) -> bool:
        return bool(self.overall_advance_balance)

    def _pay_advanced_balances(self, payment_amount: Decimal) -> Decimal:
        """Pay the "advance balance" of the *oldest* active advance,
        and if there is any remaining amount it reduces the amount
        of the following (second oldest) advance, and so on
        """
        amount_to_reduce = payment_amount
        for advance in self.advances:
            if advance['current_balance'] and amount_to_reduce:
                (
                    advance['current_balance'],
                    amount_to_reduce,
                ) = self._subtract_smaller_from_larger(
                    advance['current_balance'], amount_to_reduce
                )
        if amount_to_reduce:
            self.overall_advance_balance = Decimal(0)
        else:
            self.overall_advance_balance -= payment_amount

        return amount_to_reduce

    def _subtract_smaller_from_larger(
        self, amount1: Decimal, amount2: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """helper method to subtrac smaller amount from larger amount
        and return them in same order"""
        if amount1 < amount2:
            return Decimal(0), amount2 - amount1
        return amount1 - amount2, Decimal(0)
