from emprestimo.worker.scheduler_worker import avaliar_estado_worker


def test_health_degrada_apos_tres_ciclos_de_lag() -> None:
    assert avaliar_estado_worker(lag_segundos=61, ciclos_lag=2, falha_supervisor=False) == "healthy"
    assert (
        avaliar_estado_worker(lag_segundos=61, ciclos_lag=3, falha_supervisor=False) == "degraded"
    )


def test_health_fica_unhealthy_por_falha_do_supervisor() -> None:
    assert avaliar_estado_worker(lag_segundos=0, ciclos_lag=0, falha_supervisor=True) == "unhealthy"
