from reporter.postprocessing.text import number2kansuuzi


def test_number2kansuuzi():
    s = ['大引け', 'は', '147', '円', '高', 'の', '14000円']
    expected = ['大引け', 'は', '147', '円', '高', 'の', '1万4000円']
    result = number2kansuuzi(s)
    assert result == expected

    s = ['10000円', '台']
    expected = ['1万円', '台']
    result = number2kansuuzi(s)
    assert result == expected
