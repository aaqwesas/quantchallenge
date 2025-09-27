
from enum import Enum
from typing import Optional
import math

class Side(Enum):
    BUY = 0
    SELL = 1

class Ticker(Enum):
    # TEAM_A (home team)
    TEAM_A = 0

def place_market_order(side: Side, ticker: Ticker, quantity: float) -> None:
    """Place a market order.
    
    Parameters
    ----------
    side
        Side of order to place
    ticker
        Ticker of order to place
    quantity
        Quantity of order to place
    """
    return

def place_limit_order(side: Side, ticker: Ticker, quantity: float, price: float, ioc: bool = False) -> int:
    """Place a limit order.
    
    Parameters
    ----------
    side
        Side of order to place
    ticker
        Ticker of order to place
    quantity
        Quantity of order to place
    price
        Price of order to place
    ioc
        Immediate or cancel flag (FOK)

    Returns
    -------
    order_id
        Order ID of order placed
    """
    return 0

def cancel_order(ticker: Ticker, order_id: int) -> bool:
    """Cancel an order.
    
    Parameters
    ----------
    ticker
        Ticker of order to cancel
    order_id
        Order ID of order to cancel

    Returns
    -------
    success
        True if order was cancelled, False otherwise
    """
    return 0

class Strategy:
    """Template for a strategy."""

    def reset_state(self) -> None:
        """Reset the state of the strategy to the start of game position."""
        self.position = 0.0
        self.capital = 100000.0
        self.possession = None
        self.last_shooter = None
        self.max_time = None
        self.current_prob = 0.5
        self.home_score = 0
        self.away_score = 0
        self.time_remaining = 0.0
        self.bids = []  # list of (price, quantity) sorted descending by price
        self.asks = []  # list of (price, quantity) sorted ascending by price
        self.my_orders = {}  # dict of order_id: (side, price, quantity)
        self.streak_team = None
        self.streak_points = 0
        self.last_mid = None

    def __init__(self) -> None:
        """Your initialization code goes here."""
        self.reset_state()

    def on_trade_update(
        self, ticker: Ticker, side: Side, quantity: float, price: float
    ) -> None:
        """Called whenever two orders match."""
        print(f"Python Trade update: {ticker} {side} {quantity} shares @ {price}")

    def on_orderbook_update(
        self, ticker: Ticker, side: Side, quantity: float, price: float
    ) -> None:
        """Called whenever the orderbook changes."""
        if side == Side.BUY:
            for i in range(len(self.bids)):
                if self.bids[i][0] == price:
                    if quantity > 0:
                        self.bids[i] = (price, quantity)
                    else:
                        del self.bids[i]
                    break
            else:
                if quantity > 0:
                    self.bids.append((price, quantity))
            self.bids.sort(reverse=True)
        else:
            for i in range(len(self.asks)):
                if self.asks[i][0] == price:
                    if quantity > 0:
                        self.asks[i] = (price, quantity)
                    else:
                        del self.asks[i]
                    break
            else:
                if quantity > 0:
                    self.asks.append((price, quantity))
            self.asks.sort()

        # Trade only if mid changed significantly to avoid too frequent updates
        if self.bids and self.asks:
            mid = (self.bids[0][0] + self.asks[0][0]) / 2
            if self.last_mid is None or abs(mid - self.last_mid) >= 1.0:
                self.last_mid = mid
                self.trade()

    def on_account_update(
        self,
        ticker: Ticker,
        side: Side,
        price: float,
        quantity: float,
        capital_remaining: float,
    ) -> None:
        """Called whenever one of your orders is filled."""
        if side == Side.BUY:
            self.position += quantity
        else:
            self.position -= quantity
        self.capital = capital_remaining
        # Since we cancel and replace, we don't precisely track partial fills here

    def on_game_event_update(self,
                             event_type: str,
                             home_away: str,
                             home_score: int,
                             away_score: int,
                             player_name: Optional[str],
                             substituted_player_name: Optional[str],
                             shot_type: Optional[str],
                             assist_player: Optional[str],
                             rebound_type: Optional[str],
                             coordinate_x: Optional[float],
                             coordinate_y: Optional[float],
                             time_seconds: Optional[float]
        ) -> None:
        """Called whenever a basketball game event occurs."""

        print(f"{event_type} {home_score} - {away_score}")

        if event_type == "END_GAME":
            self.reset_state()
            return

        self.home_score = home_score
        self.away_score = away_score
        self.time_remaining = time_seconds if time_seconds is not None else self.time_remaining

        if self.max_time is None and self.time_remaining > 0:
            self.max_time = self.time_remaining

        # Update possession
        if event_type == "JUMP_BALL" and home_away != "unknown":
            self.possession = home_away
        elif event_type == "SCORE":
            if self.possession == "home":
                self.possession = "away"
            elif self.possession == "away":
                self.possession = "home"
        elif event_type == "MISSED":
            self.last_shooter = home_away
        elif event_type == "REBOUND":
            self.possession = home_away
        elif event_type == "TURNOVER":
            self.possession = "away" if home_away == "home" else "home"
        elif event_type == "STEAL":
            self.possession = home_away

        # Update streak for momentum
        if event_type == "SCORE":
            points = 3 if shot_type == "THREE_POINT" else 1 if shot_type == "FREE_THROW" else 2
            if self.streak_team != home_away:
                self.streak_team = home_away
                self.streak_points = points
            else:
                self.streak_points += points

        # Calculate win probability
        if self.time_remaining == 0:
            self.current_prob = 1.0 if self.home_score > self.away_score else 0.0
        else:
            T = self.time_remaining / self.max_time if self.max_time else 0.0
            S = self.home_score - self.away_score
            A = 0  # Home team
            P = 1.0 if self.possession == "home" else 0.0 if self.possession == "away" else 0.5
            linear_inside = 0.2775 - 0.4483 * A + 0.3208 * T * S + 0.2894 * P
            self.current_prob = 1 / (1 + math.exp(-linear_inside))

        # Trade after event
        self.trade()

    def on_orderbook_snapshot(self, ticker: Ticker, bids: list, asks: list) -> None:
        """Called periodically with a complete snapshot of the orderbook."""
        self.bids = bids
        self.asks = asks
        self.trade()

    def is_away_dominating(self) -> bool:
        """Check if away team is dominating."""
        diff = self.away_score - self.home_score
        if diff <= 0:
            return False

        if self.max_time is None:
            return False

        quarter_duration = self.max_time / 4
        if self.time_remaining > 3 * quarter_duration:  # Q1
            threshold = 10
        elif self.time_remaining > 2 * quarter_duration:  # Q2
            threshold = 15
        elif self.time_remaining > quarter_duration:  # Q3
            threshold = 12
        else:  # Q4
            threshold = 8

        score_dominate = diff >= threshold
        streak_dominate = self.streak_team == "away" and self.streak_points >= 10

        return score_dominate or streak_dominate

    def trade(self) -> None:
        """Implement the modified grid strategy."""
        if not self.bids or not self.asks:
            return

        # First, cancel all existing orders
        for order_id in list(self.my_orders.keys()):
            cancel_order(Ticker.TEAM_A, order_id)
        self.my_orders = {}

        # Clear positions if 5 minutes or less remaining
        if self.time_remaining <= 300 and self.time_remaining > 0:
            if self.position > 0:
                place_market_order(Side.SELL, Ticker.TEAM_A, self.position)
            elif self.position < 0:
                place_market_order(Side.BUY, Ticker.TEAM_A, -self.position)
            return

        # Otherwise, set up grid around fair value
        fair = self.current_prob * 100
        interval = 3.0  # Tight grid as recommended
        num_levels = 3
        qty_per_level = max(1.0, (self.capital * 0.005) / fair) if fair > 0 else 1.0  # 0.5% of capital per level

        away_dominating = self.is_away_dominating()

        for i in range(1, num_levels + 1):
            buy_price = max(0.01, fair - i * interval)  # Avoid 0 or negative
            if not away_dominating:
                order_id = place_limit_order(Side.BUY, Ticker.TEAM_A, qty_per_level, buy_price)
                if order_id:
                    self.my_orders[order_id] = (Side.BUY, buy_price, qty_per_level)

            sell_price = min(99.99, fair + i * interval)  # Avoid over 100
            order_id = place_limit_order(Side.SELL, Ticker.TEAM_A, qty_per_level, sell_price)
            if order_id:
                self.my_orders[order_id] = (Side.SELL, sell_price, qty_per_level)
