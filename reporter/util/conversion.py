from reporter.util.constant import SeqType


def stringify_ric_seqtype(ric: str, seqtype: SeqType) -> str:
    return ric + '___' + seqtype.value


def base_ric_first(num_rics: list,
                   base_ric='.N225') -> None:
    """Change the order of given ric list as to be the base ric at first element
    """
    num_rics.remove(base_ric)
    num_rics.insert(0, base_ric)
