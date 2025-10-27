# Feature Specification: ETF Data Synchronization

**Feature Branch**: `001-etf-sync`  
**Created**: 2025-01-27  
**Status**: Draft  
**Input**: User description: "需要同步ETF信息到数据库，增加字段标记为ETF，并支持ETF历史价格数据同步"

> **Note**: This specification MUST be placed in the target project's `specs/001-etf-sync/` directory (e.g., `qtfund_project_2/specs/`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sync ETF List from Remote API (Priority: P1)

System can fetch ETF list from remote HTTP API for Shanghai and Shenzhen exchanges and store them in the database with an ETF marker.

**Why this priority**: This is the foundation - ETF list must be in the database before any price data can be synchronized.

**Independent Test**: System can successfully fetch ETF list from remote API, identify them as ETFs, and store them in the database with appropriate markers.

**Acceptance Scenarios**:

1. **Given** the sync script is executed, **When** it fetches from the Shanghai ETF API, **Then** it retrieves a list of ETFs and stores them with an ETF marker field set to true
2. **Given** the sync script is executed, **When** it fetches from the Shenzhen ETF API, **Then** it retrieves ETF list and stores them with ETF marker
3. **Given** an ETF already exists in the database, **When** the sync runs, **Then** it updates the ETF information without creating duplicates
4. **Given** a new ETF is added to the remote API, **When** the sync runs, **Then** it adds the new ETF to the database with ETF marker

---

### User Story 2 - Add ETF Marker Field to Database (Priority: P1)

Database schema supports a field to distinguish ETFs from regular stocks. **Query operations are internal to the sync process only** - used to determine which ETFs need syncing and track sync status.

**Why this priority**: Without an ETF marker, the system cannot differentiate between stocks and ETFs during sync operations (e.g., which ETFs need price updates).

**Independent Test**: Database has a field (e.g., is_etf, stock_type, or instrument_type) that enables sync processes to identify and filter ETFs internally.

**Critical Clarification (2025-01-27)**: This project maintains **single responsibility**: sync data from remote API to database. Query functions in Phase 3 are **internal to the sync workflow only**:
- Query database to check if ETF already exists (duplicate detection)
- Query database to identify which ETFs need daily price updates
- Query database to determine sync progress and status
- **NOT** intended as external query API for end users

**Acceptance Scenarios**:

1. **Given** the database schema is updated with is_etf field, **When** the sync process queries the database, **Then** it can filter ETFs to determine which need price updates
2. **Given** ETF records are stored, **When** the sync checks existing records, **Then** it correctly identifies ETFs to prevent duplicates
3. **Given** the sync process queries the database, **When** filtering by is_etf field, **Then** it can determine which ETFs are missing price data
4. **Given** the database has both stocks and ETFs, **When** the sync queries for ETF list, **Then** it returns only ETFs for processing

---

### User Story 3 - Sync ETF Historical Price Data (Priority: P1)

System can fetch ETF daily price data from remote API and store them in the historical price database, using the same price sync mechanism as stocks.

**Why this priority**: ETF price history is needed for quantitative analysis, just like stock price history.

**Independent Test**: System can fetch ETF price data and store it in the price history table with the same format as stock prices.

**Acceptance Scenarios**:

1. **Given** ETFs are in the database with ETF marker, **When** the daily price sync runs, **Then** ETF prices are fetched and stored
2. **Given** the price sync API returns ETF price data in the same format, **When** data is fetched, **Then** it is stored in the same price table used for stocks
3. **Given** an ETF's price data is fetched daily, **When** users query historical data, **Then** they can see ETF price history like stock price history
4. **Given** ETF price sync fails for a specific ETF, **When** other ETFs are processed, **Then** the error doesn't block other ETF syncing

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST add an ETF marker field to the stock/instrument table in the database (e.g., is_etf boolean or stock_type enum)
- **FR-002**: System MUST fetch ETF list from "https://www.tsanghi.com/api/fin/etf/{exchange_code}/list" for SH and SZ exchanges
- **FR-003**: System MUST store fetched ETFs in the stock information table with ETF marker set to true
- **FR-004**: System MUST prevent duplicate ETF records during sync (update existing or skip)
- **FR-005**: System MUST support incremental sync (only fetch new/missing ETFs)
- **FR-006**: System MUST fetch ETF daily price data from "https://www.tsanghi.com/api/fin/etf/{exchange_code}/daily/realtime"
- **FR-007**: System MUST store ETF price data in the same price history table structure as stocks
- **FR-008**: System MUST support daily automated ETF price sync using the same scheduler as stocks
- **FR-009**: System MUST handle API errors gracefully (skip failed ETFs, log errors, continue with others)
- **FR-010**: System MUST support ETF data format matching stock data format (same response structure)
- **FR-011**: System MUST support internal queries to database for sync workflow (identify which ETFs need updating, check duplicates)
- **FR-012**: System MUST provide CLI tools to trigger ETF sync operations by extending `full_sync_v2.py` script pattern

### Out of Scope

This project maintains a **single responsibility**: **sync data from remote APIs to database**. The following are explicitly **OUT OF SCOPE**:

- **No external query API endpoints** for end users (read-only REST APIs, GraphQL, etc.)
- **No authentication or authorization** for external users (not a multi-user system)
- **No data export/import** beyond storing in database
- **No real-time query services** or websockets
- **No client-facing UI or web interface** for querying data
- Query functions are **internal only** to support sync workflows (check what needs syncing, track progress)

If query/read API functionality is needed, it should be implemented as a **separate service** that reads from the database populated by this sync system.

### Key Entities *(include if feature involves data)*

- **ETF Instrument**: Exchange-traded fund with market code, symbol, name, and ETF marker
- **ETF List**: Collection of ETFs from a specific exchange fetched from remote API
- **ETF Price Data**: Daily trading data (open, high, low, close, volume) for ETFs
- **ETF Marker Field**: Database field identifying records as ETFs vs. regular stocks
- **Sync Schedule**: Automated process that fetches and updates ETF data periodically

## Clarifications

### Session 2025-01-27

- Q: Phase 3查询功能是从数据库查还是从远程API接口查？是否应该提供对外查询API？
  → A: 查询功能仅用于同步流程内部，从数据库查询以确定哪些ETF需要同步。项目保持单一职责：从远程API同步数据到数据库。**不提供**外部查询API，查询仅用于同步流程内部辅助。
  
- Q: Phase 5的API路由是否需要实现？
  → A: **不需要实现REST API查询端点**。qtfund_project_2专注于数据同步功能，不提供对外查询API。如有需求，应创建独立的查询服务项目。Phase 5应重新定义为同步触发工具（如CLI命令）。
  
- Q: CLI触发是指的通过full_sync_v2.py脚本执行触发吗？
  → A: **是的**。ETF同步通过扩展现有的`full_sync_v2.py`脚本实现，保持一致的命令行接口模式。脚本调用Flask API（端口7777）触发同步，支持ETF列表同步和价格数据同步。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System successfully fetches ETF list for Shanghai and Shenzhen exchanges and stores all ETFs
- **SC-002**: ETF marker field correctly identifies ETFs (internal queries return only ETFs when filtering by marker)
- **SC-003**: ETF price data sync runs daily alongside stock price sync
- **SC-004**: ETF price data is stored with the same data structure as stock price data
- **SC-005**: System handles API failures gracefully (at least 90% of ETFs sync successfully even if some fail)
- **SC-006**: ETF sync process completes within acceptable time (same performance expectations as stock sync)
- **SC-007**: No duplicate ETF records are created when sync runs multiple times
- **SC-008**: ETF data is accessible in database with same structure, enabling future read access if needed (internal consistency)

