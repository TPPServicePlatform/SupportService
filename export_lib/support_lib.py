from typing import Dict, Optional
from imported_lib.SupportService.lib.exportable_strikes_nosql import Strikes

class SupportLib:
    def __init__(self, test_client=None):
        self.strikes = Strikes(test_client)

    def check_suspension(self, user_id: str) -> Optional[str]:
        return self.strikes.check_suspension(user_id)
    
    def get_all_users_suspended(self) -> set[Dict]:
        return self.strikes.get_all_suspendend()