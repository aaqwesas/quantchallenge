from enum import Enum, IntEnum, StrEnum, auto
import math
from typing import Optional

class UpperStrEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name,*args):
        return name.upper()

class team(StrEnum):
    HOME = auto()
    AWAY = auto()

class EventType(UpperStrEnum):
    JUMP_BALL = auto()
    SCORE = auto()
    MISSED = auto()
    REBOUND = auto()
    STEAL = auto()
    BLOCK = auto()
    TURNOVER = auto()
    FOUL = auto()
    TIMEOUT = auto()
    SUBSTITUTION = auto()
    START_PERIOD = auto()
    END_PERIOD = auto()
    END_GAME = auto()
    DEADBALL = auto()
    NOTHING = auto()
    UNKNOWN = auto()
    
    
class ScoringEvent(UpperStrEnum):
    THREE_POINT = auto()
    TWO_POINT = auto()
    FREE_THROW = auto()
    DUNK = auto()
    LAYUP = auto()

class TradeSetting(IntEnum):
    MIN_EDGE = 10
    MAX_EDGE = 30
    MAX_EXPOSURE_PCT = 70   # percentage
    MAX_ORDERS_PER_SIDE = 25
    ORDER_LIFETIME_SEC = 5
    SPREAD_CAPTURE_THRESHOLD = 10.0
    INITIAL_CAPITAL = 100_000
    TAKE_PROFIT_THRESHOLD = 2

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
    def reset_state(self) -> None:
        """Reset the state of the strategy to the start of game position.
        
        Note: In production execution, the game will start from the beginning
        and will not be replayed.
        """
        self.position = 0
        self.win_probability = 0.5 # natural
        self.bids = [] # bids order from the orderbook
        self.asks = [] # asks order from the orderbook
        
        self.home_score = 0 
        self.away_score = 0
        self.time_seconds = 2880.0
        self.last_event_time = 2880.0
        # self.possession_team = "unknown"
        self.open_orders  = {}
        self.capital_remaining = TradeSetting.INITIAL_CAPITAL
        self.avg_entry_price = 0.0
        
        
        # self.shot_attempts = defaultdict(int)
        # self.shot_makes = defaultdict(int)
        
    def get_best_bid(self) -> float: 
        """ get best bid from orderbook """
        return self.bids[0][0] if self.bids else 0.0
    
    def get_best_ask(self) -> float:
        """ get best ask from orderbook """
        return self.asks[0][0] if self.asks else 100.0

    def update_win_probability(self) -> None:
        score_diff = self.home_score - self.away_score
        time_left = max(1.0,self.time_seconds)

        score_diff_scaling = 0.4
        base_prob = 0.5 + (score_diff * score_diff_scaling) / time_left

        prob = 1 / (1 + math.exp(-base_prob))
        self.win_probability = max(0.01, min(0.99,prob))
    
    def calculate_order_quantity(self, edge_cents) -> float:
        
        base_qty = edge_cents / 100.0
        
        scaled_qty = max(1.0,min(
         base_qty * 1.0,
         self.capital_remaining / 100 * 0.1,
         (TradeSetting.MAX_EXPOSURE_PCT / 100.0 * TradeSetting.INITIAL_CAPITAL) / 100.0 - abs(self.position)
        ))
        
        return round(scaled_qty,1)
    
    def should_place_order(self, side: Side, limit_price: float, qty:float) -> bool:
        best_ask = self.get_best_ask() 
        best_bid = self.get_best_bid()
        
        if side == Side.BUY and limit_price >= best_ask:
            return False    
        if side == Side.SELL and limit_price <= best_bid:
            return False

        exposure_after= self.position + (qty if side == Side.BUY else -qty)
        max_allowed = (TradeSetting.MAX_EXPOSURE_PCT/ 100.0 * TradeSetting.INITIAL_CAPITAL) / 100.0
        if abs(exposure_after) > max_allowed:
            return False
        
        return True
    
    def place_smart_order(self,side: Side, target_price: float, edge_buffer: float, edge: int, order_type="limit") -> None:
        if len([o for o in self.open_orders.values() if o["side"] == side]) >= TradeSetting.MAX_ORDERS_PER_SIDE:
            return
        
        limit_price = round(target_price - (edge_buffer if side == Side.BUY else -edge_buffer), 2)
        limit_price = max(0.01, min(99.99, limit_price))
         
        qty = self.calculate_order_quantity(edge)
        
        if not self.should_place_order(side,limit_price,qty):
            return
        
        print(f"Order placed: type: {order_type}, side:{side.name}, target price: {target_price}, qty: {qty} ")
        if order_type == "limit":
            order_id = place_limit_order(side,Ticker.TEAM_A,qty,limit_price)
            
            self.open_orders[order_id] = {
                'side': side,
                'price': limit_price,
                'qty': qty,
                'placed_at_time': self.last_event_time
            }
        else:
            place_market_order(side,Ticker.TEAM_A,qty)
            
        
    def evaluate_and_trade(self) -> None:
        fair = self.win_probability * 100
        best_ask = self.get_best_ask()
        best_bid = self.get_best_bid()
        buy_edge = fair - best_ask
        sell_edge = best_bid - fair
        spread = best_ask - best_bid

        stale_ids = [
            oid for oid, o in self.open_orders.items()
            if o["placed_at_time"] - self.last_event_time > TradeSetting.ORDER_LIFETIME_SEC
        ]
        
        for oid in stale_ids:
            cancel_order(Ticker.TEAM_A, oid)
            self.open_orders.pop(oid,None)
        
        if self.position != 0:
            unrealized = (fair - self.avg_entry_price) if self.position > 0 else (self.avg_entry_price - fair)
            if unrealized > TradeSetting.TAKE_PROFIT_THRESHOLD:
                close_side = Side.SELL if self.position > 0 else Side.BUY
                close_qty = abs(self.position)
                place_market_order(close_side, Ticker.TEAM_A, close_qty)
                self.position = 0
                self.avg_entry_price = 0
        
        
        #Market Making logic (always try to have some order in the market)
        gamma = 0.05
        skew = self.position * gamma
        reservation = fair - skew
        half_spread = 0.5
        
        buy_orders = [o for o in self.open_orders.values() if o["side"] == Side.BUY]
        if len(buy_orders) < TradeSetting.MAX_ORDERS_PER_SIDE:
            self.place_smart_order(Side.BUY,reservation,half_spread,edge=3.0)     
        sell_orders = [o for o in self.open_orders.values() if o["side"] == Side.SELL]
        if len(sell_orders) < TradeSetting.MAX_ORDERS_PER_SIDE:
            self.place_smart_order(Side.SELL,reservation,half_spread,edge=3.0)
        
        # Directional trading
        if buy_edge > TradeSetting.MIN_EDGE:
            order_type = "market" if buy_edge > TradeSetting.MAX_EDGE else "limit"
            self.place_smart_order(Side.BUY,fair, edge_buffer=5.0, edge=buy_edge,order_type=order_type)
        if sell_edge > TradeSetting.MIN_EDGE:
            order_type = "market" if sell_edge > TradeSetting.MAX_EDGE else "limit"
            self.place_smart_order(Side.SELL,fair, edge_buffer=5.0, edge=sell_edge,order_type=order_type)
            
        # Capturing the Spread
        if (spread > TradeSetting.SPREAD_CAPTURE_THRESHOLD and
                best_bid <  fair < best_ask
                ):
                self.place_smart_order(Side.BUY, fair, edge_buffer=3.0, edge=abs(buy_edge),order_type="market")
                self.place_smart_order(Side.SELL, fair, edge_buffer=3.0, edge=abs(sell_edge), order_type="market")
            
        
    def __init__(self) -> None:
        """Your initialization code goes here."""
        self.reset_state()


    def on_trade_update(
        self, ticker: Ticker, side: Side, quantity: float, price: float
    ) -> None:
        """
        Called whenever two orders match. Could be one of your orders, or two other people's orders.
        """
        self.evaluate_and_trade()

    def on_orderbook_update(
        self, ticker: Ticker, side: Side, quantity: float, price: float
    ) -> None:
        """
        Called whenever the orderbook changes. This could be because of a trade, or because of a new order, or both.
        """
        book = self.bids if side == Side.BUY else self.asks
        i = 0
        while i < len(book):
            if abs(book[i][0] - price) < 1e-5:
                del book[i]
            else:
                i += 1
        
        if quantity > 0:
            new_entry = (price, quantity)
            book.append(new_entry)
            
            if side == Side.BUY:
                book.sort(key=lambda x: x[0], reverse=True)
            else:
                book.sort(key=lambda x: x[0])
                
        # if self.time_seconds < 2880.0:
        #     self.evaluate_and_trade()

    def on_account_update(
        self,
        ticker: Ticker,
        side: Side,
        price: float,
        quantity: float,
        capital_remaining: float,
    ) -> None:
        """
        Called whenever one of your orders is filled.
        """
        self.capital_remaining = capital_remaining
        old_position = self.position
        self.position += quantity if side == Side.BUY else -quantity
        
        if old_position == 0:
            self.avg_entry_price = price
        else:
            direction = 1 if side == Side.BUY else -1
            self.avg_entry_price = (self.avg_entry_price * abs(old_position) + price * quantity * direction) / abs(self.position) if self.position != 0 else 0.0
            
        for oid in list(self.open_orders.keys()):
            o = self.open_orders[oid]
            if o["side"] == side and abs(o["price"] - price) < 0.01:
                o["qty"] -= quantity
                if o["qty"] <= 0:
                    del self.open_orders[oid]
                break
        print(f"FILLED : {side.name}, {quantity} @{price}. Position: {self.position}")
        print(f"capital remaining: {capital_remaining}")
    

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
        """
        Called whenever a basketball game event occurs.
        """
        self.home_score = home_score
        self.away_score = away_score
        if time_seconds is not None:
            self.time_seconds = time_seconds
        self.last_event_time = self.time_seconds
        # if event_type == EventType.TURNOVER:
        #     self.possession_team = team.AWAY if home_away == team.HOME else team.HOME
        # elif event_type == EventType.REBOUND:
        #    self.possession_team = home_away
        # elif event_type == EventType.STEAL:
        #     self.possession_team = home_away
                
        self.update_win_probability()
        self.evaluate_and_trade()
        print(f"{event_type} {home_score} - {away_score}")

        if event_type == EventType.END_GAME:
            self.reset_state()

    def on_orderbook_snapshot(self, ticker: Ticker, bids: list, asks: list) -> None:
        """
        Called periodically with a complete snapshot of the orderbook.
        This provides the full current state of all bids and asks, useful for 
        verification and algorithms that need the complete market picture.
        """
        # Reset the state of local books
        self.bids = bids
        self.asks = asks
        self.evaluate_and_trade()
        
    
