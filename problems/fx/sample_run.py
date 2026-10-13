"""Happy-path demonstration of the FX desk."""
from question import Desk, plan_settlement

RATES = {
    "EURUSD": 10_842,
    "GBPUSD": 12_650,
    "JPYUSD": 68,
}


def main() -> None:
    desk = Desk(
        seed_cents=10_000_000,
        rate_source=lambda pair: RATES.get(pair, 10_000),
    )

    desk.submit("Alice", "EURUSD", 500_000)
    desk.submit("Bob", "GBPUSD", 3_000_000)
    desk.submit("Carol", "JPYUSD", 15_000_000)

    session = desk.close()
    print(f"Session closed. Requests: {len(session.requests)}. Seed: {session.seed_cents} cents.")

    try:
        report = plan_settlement(session)
        print(f"Settlements: {len(report.settlements)}")
        for s in report.settlements:
            print(
                f"  {s.participant} {s.pair} "
                f"{s.notional_cents} cents → {s.usd_cents} USD cents "
                f"(spread {s.spread_bps} bps)"
            )
        print(f"Total USD: {report.total_usd_cents} cents")
        print(f"Rollover:  {report.rollover_cents} cents")
    except NotImplementedError:
        print("plan_settlement is not yet implemented.")


if __name__ == "__main__":
    main()
