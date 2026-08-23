"""Adapters de canais de notificacao."""

from emprestimo.infrastructure.notifications.resend import ResendNotificationChannel
from emprestimo.infrastructure.notifications.whatsapp import EvolutionWhatsAppNotificationChannel

__all__ = ["EvolutionWhatsAppNotificationChannel", "ResendNotificationChannel"]
