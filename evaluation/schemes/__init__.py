"""Evaluation schemes sub-package."""

from .proposed import ProposedScheme
from .ref3 import Ref3Scheme
from .ref6 import Ref6Scheme
from .ref20 import Ref20Scheme

SCHEME_REGISTRY = {
    "Proposed": ProposedScheme,
    "Ala'anzy et al.": Ref3Scheme,
    "Jasim & Al-Raweshidy": Ref6Scheme,
    "Kashyap et al.": Ref20Scheme,
}
