import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.utils.time import now as local_now


class Base(DeclarativeBase):
    pass


class CardType(str, enum.Enum):
    UZCARD = "uzcard"
    HUMO = "humo"


class Category(str, enum.Enum):
    OZIQ_OVQAT = "Oziq-ovqat"
    TRANSPORT = "Transport"
    KOMMUNAL = "Kommunal"
    KIYIM = "Kiyim"
    SOGLIQ = "Sog'liqni saqlash"
    TALIM = "Ta'lim"
    KONGILOCHAR = "Ko'ngilochar"
    UY_ROZGOR = "Uy-ro'zg'or"
    TELEFON = "Telefon"
    QARZ_BERISH = "Qarz berish"
    NAQDLASHTIRISH = "Naqdlashtirish"
    BOSHQA = "Boshqa"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (Index("ix_expenses_user_time", "user_id", "transaction_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Xarajatga hisoblanadigan summa (ulush ajratilgan bo'lsa — faqat o'z qismi)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    # NULL = to'lov to'liq o'ziniki. Aks holda — kartadan chiqqan asl (umumiy) summa
    original_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    # NULL = hali kategoriyalanmagan (pending) — userbot avtomatik saqlaganda shunday bo'ladi
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    card_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(10), nullable=True)
    balance_after: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    forward_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    forward_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Manba: 'forward' (qo'lda), 'userbot' (avtomatik), 'manual' (qo'lda summa)
    source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Mahalliy (TIMEZONE) vaqt — `transaction_time` bilan bir xil o'lchovda.
    # Ilgari bu yerda `datetime.utcnow()` turardi va ikkalasi `coalesce()` bilan
    # aralashtirilgani uchun tartib ham, "Shu oy" chegarasi ham siljigan edi.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=local_now)


class Setting(Base):
    """Kalit-qiymat sozlamalar (masalan, botlarni avtomatik o'qish on/off)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
