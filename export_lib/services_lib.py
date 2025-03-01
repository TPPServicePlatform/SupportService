from typing import Dict
from imported_lib.SupportService.lib.exportable_strikes_nosql import Strikes

class ServicesLib:
    def __init__(self, test_client=None):
        self.strikes = Strikes(test_client)

    def is_user_suspended(self, user_id: str) -> bool:
        return self.strikes.is_user_suspended(user_id)
    
    def get_all_users_suspended(self) -> list[Dict]:
        return self.strikes.get_all_suspendend()