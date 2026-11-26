"""Cálculos de CQI para uma medição por corrida e referências fixas."""
import math
from statistics import mean, stdev


def number(value, field):
    """Aceita vírgula decimal; rejeita campos vazios, NaN e infinito."""
    try:
        if isinstance(value, bool):
            raise ValueError
        result = float(str(value).strip().replace(',', '.'))
        if not math.isfinite(result) or abs(result) > 1e12:
            raise ValueError
        return result
    except (TypeError, ValueError):
        raise ValueError(f'{field}: informe um número finito entre -10¹² e 10¹².') from None


def evaluate(previous, result, target, sd):
    """Avalia a última corrida, sem misturar séries ou recalcular o alvo.

    Variante moderna: 4_1s e 10x independem de um alerta 1_2s prévio.
    R_4s não se aplica a medições de corridas diferentes.
    """
    if sd <= 0:
        raise ValueError('Desvio padrão deve ser maior que zero.')
    z = [(value - target) / sd for value in [*previous[-9:], result]]
    if not all(math.isfinite(value) for value in z):
        raise ValueError('Desvio padrão pequeno demais para os resultados informados.')
    rules = []
    if abs(z[-1]) > 2:
        rules.append('1_2s')
    if abs(z[-1]) > 3:
        rules.append('1_3s')
    for count, limit, name in [(2, 2, '2_2s'), (4, 1, '4_1s'), (10, 0, '10x')]:
        tail = z[-count:]
        if len(tail) == count and (all(v > limit for v in tail) or all(v < -limit for v in tail)):
            rules.append(name)
    status = 'Rejeitado' if any(r != '1_2s' for r in rules) else ('Alerta' if rules else 'Aceito')
    return {'z': z[-1], 'regras': rules, 'status': status}


def summary(values):
    """Estatísticas observadas são descritivas; não substituem a referência."""
    return {'n': len(values), 'media': mean(values) if values else None,
            'desvio_amostral': stdev(values) if len(values) > 1 else None}
