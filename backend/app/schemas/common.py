from typing import Literal

# The state of one dependency, as shown on the Dashboard.
CheckState = Literal["ok", "not_configured", "unreachable", "error"]
