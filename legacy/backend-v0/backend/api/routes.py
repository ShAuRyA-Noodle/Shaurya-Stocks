@router.get("/positions")
def get_positions():
    state = load_portfolio_state()
    return {
        "positions": list(state["positions"].values()),
        "cash": state["cash"],
        "unrealized_pnl": state["unrealized_pnl"],
    }
