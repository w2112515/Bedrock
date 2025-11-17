"""
Account Service - Business logic for account management.
"""

import sys
import os
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.core.config import settings
from services.portfolio.app.models.account import Account

logger = setup_logging("account_service")


class AccountService:
    """
    Account management service.
    
    Provides business logic for account operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize AccountService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_account(self) -> Account:
        """
        Get the default account.
        
        Creates account if it doesn't exist.
        
        Returns:
            Account object
        """
        try:
            account = self.db.query(Account).first()
            
            if not account:
                logger.info("Account not found. Creating default account.")
                account = self.initialize_default_account()
            
            logger.info(
                f"Retrieved account: id={account.id}, "
                f"balance={account.balance}, available={account.available_balance}"
            )
            
            return account
            
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            raise
    
    def initialize_default_account(self) -> Account:
        """
        Initialize default account with configured initial balance.
        
        Returns:
            Created Account object
        """
        try:
            # Check if account already exists
            existing_account = self.db.query(Account).first()
            if existing_account:
                logger.warning("Account already exists. Returning existing account.")
                return existing_account
            
            # Create new account
            account = Account(
                id=UUID(settings.DEFAULT_ACCOUNT_ID),
                balance=settings.INITIAL_BALANCE,
                available_balance=settings.INITIAL_BALANCE,
                frozen_balance=Decimal('0')
            )
            
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            
            logger.info(
                f"Default account created: id={account.id}, "
                f"initial_balance={settings.INITIAL_BALANCE}"
            )
            
            return account
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error initializing default account: {e}")
            raise

