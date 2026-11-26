import pytest
from quality import evaluate, number, summary


@pytest.mark.parametrize('previous,result,rules,status', [
    ([], 100, [], 'Aceito'),
    ([], 104, [], 'Aceito'),  # igualdade ao limite não o excede
    ([], 104.1, ['1_2s'], 'Alerta'),
    ([], 106, ['1_2s'], 'Alerta'),
    ([], 106.1, ['1_2s', '1_3s'], 'Rejeitado'),
    ([104.1], 105, ['1_2s', '2_2s'], 'Rejeitado'),
    ([95.9], 95, ['1_2s', '2_2s'], 'Rejeitado'),
    ([104.1], 95, ['1_2s'], 'Alerta'),  # não aplica R_4s entre corridas
    ([103]*3, 103, ['4_1s'], 'Rejeitado'),
    ([97]*3, 97, ['4_1s'], 'Rejeitado'),
    ([101]*9, 101, ['10x'], 'Rejeitado'),
    ([99]*9, 99, ['10x'], 'Rejeitado'),
    ([101]*8+[100], 101, [], 'Aceito'),
    ([103]*2, 103, [], 'Aceito'),
])
def test_rules(previous, result, rules, status):
    actual = evaluate(previous, result, 100, 2)
    assert actual['regras'] == rules
    assert actual['status'] == status


@pytest.mark.parametrize('value', ['', None, 'NaN', 'Infinity', '1e309', True, '1.000,1'])
def test_invalid_number(value):
    with pytest.raises(ValueError):
        number(value, 'resultado')


def test_decimal_and_summary():
    assert number('93,7', 'resultado') == 93.7
    assert summary([100])['desvio_amostral'] is None
    assert summary([98, 100, 102]) == {'n': 3, 'media': 100, 'desvio_amostral': 2}
    with pytest.raises(ValueError):
        evaluate([], 100, 100, 0)
