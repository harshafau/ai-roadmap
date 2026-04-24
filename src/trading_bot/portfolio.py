"""SQLAlchemy-backed ledger for simulated (paper) fills and positions."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import Float, Integer, String, DateTime, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(4))  # BUY / SELL
    qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(8))  # paper / live
    reason: Mapped[str] = mapped_column(String(128), default="")


class Position(Base):
    __tablename__ = "positions"
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    qty: Mapped[int] = mapped_column(Integer, default=0)
    avg_price: Mapped[float] = mapped_column(Float, default=0.0)


class Portfolio:
    def __init__(self, database_url: str, starting_cash: float):
        self.engine = create_engine(database_url, future=True)
        Base.metadata.create_all(self.engine)
        self._starting_cash = starting_cash

    def apply_fill(self, symbol: str, side: str, qty: int, price: float, mode: str, reason: str = "") -> Order:
        with Session(self.engine) as s, s.begin():
            order = Order(symbol=symbol, side=side, qty=qty, price=price, mode=mode, reason=reason)
            s.add(order)

            pos = s.get(Position, symbol)
            if pos is None:
                pos = Position(symbol=symbol, qty=0, avg_price=0.0)
                s.add(pos)

            if side == "BUY":
                new_qty = pos.qty + qty
                pos.avg_price = (pos.avg_price * pos.qty + price * qty) / new_qty if new_qty else 0.0
                pos.qty = new_qty
            else:  # SELL
                pos.qty -= qty
                if pos.qty == 0:
                    pos.avg_price = 0.0
            s.flush()
            s.refresh(order)
            # Detach so callers can read fields after the session closes.
            s.expunge(order)
            return order

    def positions(self) -> list[Position]:
        with Session(self.engine) as s:
            return list(s.scalars(select(Position).where(Position.qty != 0)))

    def orders(self) -> Iterable[Order]:
        with Session(self.engine) as s:
            return list(s.scalars(select(Order).order_by(Order.ts)))

    def cash_invested(self) -> float:
        return sum(p.qty * p.avg_price for p in self.positions())

    def starting_cash(self) -> float:
        return self._starting_cash
