"""Raeburn Brain AI core package."""

from .config import Settings, settings
from .core import (
    BanditRouter,
    Context,
    ContextInjector,
    MemoryStore,
    ShardedMemoryStore,
    BanditStrategy,
    UCB1Strategy,
    ThompsonStrategy,
    SoftmaxStrategy,
    Telemetry,
    ROUTER_LATENCY,
    ROUTER_FAILURES,
)
from .memory import (
    MemoryEntry,
    InMemoryBackend,
    TinyDBBackend,
    SQLiteBackend,
    PostgresBackend,
    FaissBackend,
    PgvectorBackend,
    ingest_logs,
)
from .model import (
    BaseModelFetcher,
    FetcherStats,
    LocalModelFetcher,
    RemoteModelFetcher,
    CachedModelFetcher,
    OpenAIModelFetcher,
    OpenAIHTTPFetcher,
    HuggingFaceFetcher,
    ClaudeModelFetcher,
    ModelMetricsStore,
    ModelRegistry,
)
from .agent import Agent, AgentRegistry, AgentModel, generate_persona
from .db import run_migrations
from .prompt import PromptManager
from .server import create_app, configure_logging, MemoryLogHandler
from .meta import Mission, MissionOutcomeStore, MetaAgentScheduler
from .judging import CompetitionResult, Judge
from .business import BusinessFactory, BusinessMetricsStore, Business
from pathlib import Path
from .plugins import Plugin, PluginManager
from .comm import TelegramAdapter, TelegramBot, SlackAdapter, DiscordAdapter, VoicePipeline

plugin_manager = PluginManager(Path(__file__).resolve().parent / "plugins")

__all__ = [
    "Settings",
    "settings",
    "MemoryStore",
    "ShardedMemoryStore",
    "MemoryEntry",
    "InMemoryBackend",
    "TinyDBBackend",
    "SQLiteBackend",
    "PostgresBackend",
    "FaissBackend",
    "PgvectorBackend",
    "ingest_logs",
    "ContextInjector",
    "Context",
    "BanditStrategy",
    "UCB1Strategy",
    "ThompsonStrategy",
    "SoftmaxStrategy",
    "Telemetry",
    "ROUTER_LATENCY",
    "ROUTER_FAILURES",
    "BanditRouter",
    "Agent",
    "AgentRegistry",
    "AgentModel",
    "generate_persona",
    "run_migrations",
    "BaseModelFetcher",
    "LocalModelFetcher",
    "RemoteModelFetcher",
    "CachedModelFetcher",
    "OpenAIModelFetcher",
    "OpenAIHTTPFetcher",
    "HuggingFaceFetcher",
    "ClaudeModelFetcher",
    "ModelMetricsStore",
    "ModelRegistry",
    "FetcherStats",
    "PromptManager",
    "Mission",
    "MissionOutcomeStore",
    "MetaAgentScheduler",
    "create_app",
    "configure_logging",
    "MemoryLogHandler",
    "CompetitionResult",
    "Judge",
    "BusinessFactory",
    "BusinessMetricsStore",
    "Business",
    "Plugin", 
    "PluginManager", 
    "plugin_manager", 
    "TelegramAdapter",
    "TelegramBot",
    "SlackAdapter",
    "DiscordAdapter",
    "VoicePipeline",
]
