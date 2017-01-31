import operator



def binaryBytesToHex(byteString) -> str:
    return hex(int("".join([str(b) for b in byteString]), 2))


def hamming(str1, str2):
    assert len(str1) == len(str2)
    # ne = str.__ne__  ## this is surprisingly slow
    ne = operator.ne
    return sum(map(ne, str1, str2))
