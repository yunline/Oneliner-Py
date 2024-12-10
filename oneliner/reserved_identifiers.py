from typing import TypeAlias

import oneliner.utils as utils

_ol_reserved_name: TypeAlias = str


OL_BREAK: _ol_reserved_name = "__ol_break_{}"
OL_INTERRUPT: _ol_reserved_name = "__ol_interrupt_{}"
OL_WRAPPED_ITER: _ol_reserved_name = "__ol_it_{}"
OL_ITER_WRAPPER: _ol_reserved_name = "__ol_iter_wrapper"  # don't need format here
OL_ASSIGN_TMP: _ol_reserved_name = "__ol_assign_{}"
OL_AUGASSIGN_TMP: _ol_reserved_name = "__ol_augass_{}"
OL_AUGASSIGN_SLICE_TMP: _ol_reserved_name = "__ol_sllice_{}"
OL_RETURN_VALUE: _ol_reserved_name = "__ol_retv_{}"
OL_RETURN: _ol_reserved_name = "__ol_ret_{}"
OL_NONLOCAL_DICT: _ol_reserved_name = "__ol_nonlocal_{}"
OL_CLASS_DICT: _ol_reserved_name = "__ol_classnsp_{}"
OL_CLASS_LOADER: _ol_reserved_name = "__ol_loader_{}"
OL_IMPORT_TMP: _ol_reserved_name = "__ol_mod_{}"
OL_RUN: _ol_reserved_name = "__ol_run"


def ol_name(name: _ol_reserved_name):
    return name.format(utils.unique_id())
