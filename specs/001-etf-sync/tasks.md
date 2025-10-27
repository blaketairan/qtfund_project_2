# Tasks: ETF Data Synchronization

**Feature**: 001-etf-sync  
**Input**: Design documents from `/specs/001-etf-sync/`  
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not requested in this feature specification  
**Organization**: Tasks grouped by user story for independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], [US3])
- Include exact file paths in descriptions

---

## Phase 1: Foundation - Database Schema Extension (Priority: P1) 🎯 MVP

**Goal**: Add ETF marker field to database schema to support ETF data identification

**Independent Test**: Database schema has `is_etf` field in `stock_info` table that can be queried to filter ETFs

### Implementation

- [x] T001 [US2] Add is_etf column to StockInfo model in models/stock_data.py
- [x] T002 [US2] Create database migration script in database/migrations/add_etf_field.py
- [x] T003 [US2] Add is_etf index to StockInfo in models/stock_data.py
- [x] T004 [US2] Add composite index for ETF by market in models/stock_data.py
- [x] T005 [US2] Update existing database records with is_etf='N' via migration
- [x] T006 [US2] Add validation logic for is_etf field in StockInfo model
- [ ] T007 [US2] Test database schema changes with direct SQL queries

**Checkpoint**: Database schema ready - ETF marker field available for use

---

## Phase 2: User Story 1 - Sync ETF List from Remote API (Priority: P1)

**Goal**: System can fetch ETF list from remote API for Shanghai and Shenzhen exchanges and store them in database with ETF marker

**Independent Test**: System can fetch ETF list from remote API, identify them as ETFs, and store them with ETF marker field set to 'Y'

### Implementation

- [x] T008 [P] [US1] Create ETF API fetcher class in data_fetcher/etf_api.py
- [x] T009 [US1] Implement fetch_etf_list method in data_fetcher/etf_api.py for XSHG exchange
- [x] T010 [US1] Implement fetch_etf_list method in data_fetcher/etf_api.py for XSHE exchange
- [x] T011 [US1] Add error handling and retry logic in data_fetcher/etf_api.py
- [x] T012 [P] [US1] Create ETF sync service in app/services/etf_sync_service.py
- [x] T013 [US1] Implement sync_etf_lists method in app/services/etf_sync_service.py
- [x] T014 [US1] Add data conversion from API to StockInfo format in app/services/etf_sync_service.py
- [x] T015 [US1] Implement duplicate detection and update logic in app/services/etf_sync_service.py
- [x] T016 [US1] Set is_etf='Y' when storing ETF records via sync service
- [x] T017 [US1] Add logging for ETF sync operations in app/services/etf_sync_service.py
- [x] T018 [US1] Implement incremental sync logic to skip existing ETFs
- [x] T019 [US1] Create Flask API endpoint for ETF list sync in app/routes/sync_tasks.py
- [ ] T020 [US1] Test ETF list sync with both Shanghai and Shenzhen exchanges
- [x] T020b [US1] Add ETF sync support to full_sync_v2.py using one-by-one pattern

**Checkpoint**: ETF list sync functional - ETFs stored with is_etf='Y' marker

---

## Phase 3: User Story 2 - Add ETF Marker Query Support (Priority: P1)

**Goal**: Database supports queries to filter and distinguish ETFs from regular stocks

**Independent Test**: Database queries can filter ETFs using is_etf field (WHERE is_etf='Y')

**Note**: This story is largely covered by Phase 1, but adds query/service layer support

### Implementation

- [x] T021 [P] [US2] Add filter by is_etf query method in app/services/stock_info_service.py
- [x] T022 [US2] Add get_etf_list method to query ETFs only in app/services/stock_info_service.py
- [x] T023 [US2] Add get_etf_count_by_market helper method in app/services/stock_info_service.py
- [ ] T024 [US2] Update existing query methods to support is_etf filter parameter
- [ ] T025 [US2] Test ETF filtering queries return only ETFs
- [ ] T026 [US2] Test ETFs can be queried by market (SH/SZ) with is_etf filter

**Checkpoint**: ETF marker query support ready - API can filter ETFs

---

## Phase 4: User Story 3 - Sync ETF Historical Price Data (Priority: P1)

**Goal**: System can fetch ETF daily price data and store in same price history table as stocks

**Independent Test**: System can fetch ETF price data and store in stock_daily_data table, accessible via same queries as stock prices

### Implementation

- [x] T027 [P] [US3] Implement fetch_etf_daily_data method in data_fetcher/etf_api.py
- [x] T028 [US3] Add ETF price data fetching for XSHG exchange in data_fetcher/etf_api.py
- [x] T029 [US3] Add ETF price data fetching for XSHE exchange in data_fetcher/etf_api.py
- [x] T030 [US3] Add date range support for ETF price history in data_fetcher/etf_api.py
- [x] T031 [P] [US3] Implement sync_etf_prices method in app/services/etf_sync_service.py
- [x] T032 [US3] Add data conversion from ETF API to StockDailyData format
- [x] T033 [US3] Implement batch processing for ETF price sync
- [x] T034 [US3] Add error handling for failed ETF price fetches (skip failed, continue with others)
- [x] T035 [US3] Implement incremental sync logic for ETF prices (skip existing dates)
- [x] T036 [US3] Add logging for ETF price sync progress
- [x] T037 [US3] Integrate ETF price sync with existing background task scheduler
- [ ] T038 [US3] Test ETF price data stored in same table as stocks
- [ ] T039 [US3] Test ETF price queries work with existing price query endpoints
- [ ] T040 [US3] Verify ETF prices and stock prices can be queried together

**Checkpoint**: ETF price sync functional - ETF prices stored and queryable

---

## Phase 5: Sync API Integration (Updated Scope)

**Goal**: Add Flask API endpoints for triggering ETF sync operations (internal sync workflow only)

**Note**: Based on clarifications, this project maintains single responsibility: sync data from remote API to database. **No external query API endpoints** are provided. Phase 5 focuses on sync trigger endpoints for CLI/automation tools.

**Independent Test**: ETF sync can be triggered via Flask API and executes successfully

### Implementation

- [x] T041 [US1] Add POST /api/etf/lists endpoint for triggering ETF list sync in app/routes/sync_tasks.py
- [x] T042 [US3] Add POST /api/etf/prices endpoint for triggering ETF price sync in app/routes/sync_tasks.py
- [x] T047 [US1] Register sync_tasks blueprint in app/main.py (already registered, added ETF endpoint info)
- [ ] T048 [US1] Test ETF list sync endpoint triggers sync successfully
- [ ] T049 [US3] Test ETF price sync endpoint triggers sync successfully

**Checkpoint**: ETF sync API endpoints functional for triggering sync operations

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Documentation & Cleanup

- [ ] T054 [P] Update API documentation to include ETF endpoints
- [ ] T055 [P] Add ETF sync examples to quickstart.md
- [ ] T056 [P] Update database schema documentation with is_etf field
- [ ] T057 Add ETF data model diagrams to documentation

### Performance & Optimization

- [ ] T058 [P] Optimize ETF query performance with proper indexes
- [ ] T059 [P] Add connection pooling considerations for ETF sync
- [ ] T060 Implement API rate limiting for ETF endpoints

### Code Quality

- [ ] T061 [P] Run linter and fix code style issues
- [ ] T062 [P] Add type hints for ETF API methods
- [ ] T063 Add comprehensive docstrings for ETF sync methods
- [ ] T064 Refactor any code duplication between stock and ETF sync

### Testing & Validation

- [ ] T065 [P] Test ETF sync handles API failures gracefully
- [ ] T066 [P] Test ETF sync performance (10+ ETFs/sec requirement)
- [ ] T067 Test ETF queries meet <500ms response time requirement
- [ ] T068 Test ETF data integrity and data retention
- [ ] T069 Run end-to-end ETF sync workflow validation
- [ ] T070 Verify ETF data queryable by existing stock API endpoints (SC-008)

**Checkpoint**: Feature complete, tested, and polished

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundation)**: No dependencies - can start immediately
- **Phase 2 (US1 - ETF List Sync)**: Depends on Phase 1 completion (needs is_etf field)
- **Phase 3 (US2 - Query Support)**: Depends on Phase 1, can start in parallel with Phase 2
- **Phase 4 (US3 - Price Sync)**: Depends on Phase 2 (needs ETF list first)
- **Phase 5 (API Routes)**: Depends on Phase 2, 3, 4
- **Phase 6 (Polish)**: Depends on all previous phases

### Task Dependencies

**Within Phase 1**:
- T001 → T002 → T003, T004 → T005 → T006 → T007

**Within Phase 2 (US1)**:
- T008 → T009, T010 → T011
- T012 → T013 → T014 → T015 → T016 → T017 → T018
- T020 tests all previous tasks

**Within Phase 3 (US2)**:
- T021, T022, T023 can run in parallel
- All depend on Phase 1 completion

**Within Phase 4 (US3)**:
- T027 → T028, T029 → T030
- T031 → T032 → T033 → T034 → T035 → T036 → T037
- T038, T039, T040 test implementation

**Within Phase 5**:
- T041 → T042, T043, T044, T045, T046 → T047
- T048, T049 run after endpoints
- T050-T053 test all endpoints

### Parallel Opportunities

- All Phase 1 tasks with [P] can run in parallel
- T008-T012 can run in parallel (ETF API and ETF sync service initialization)
- T027-T031 can run in parallel (price sync API and service)
- T041-T045 (different endpoints) can run in parallel
- All Phase 6 tasks marked [P] can run in parallel

---

## Parallel Execution Examples

### Example 1: ETF List Sync (US1)

```bash
# Parallel: Initialize ETF API fetcher and sync service
Task T008: Create ETF API fetcher class in data_fetcher/etf_api.py
Task T012: Create ETF sync service in app/services/etf_sync_service.py
```

### Example 2: ETF Price Sync (US3)

```bash
# Parallel: Initialize price fetching API and sync service
Task T027: Implement fetch_etf_daily_data in data_fetcher/etf_api.py
Task T031: Implement sync_etf_prices in app/services/etf_sync_service.py
```

### Example 3: API Endpoints (Phase 5)

```bash
# Parallel: Different endpoint implementations
Task T042: Implement GET /api/v1/etf/list endpoint
Task T044: Implement GET /api/v1/etf/info/{symbol} endpoint
Task T045: Implement GET /api/v1/etf/prices/{symbol} endpoint
```

---

## Implementation Strategy

### MVP First (Phase 1 Only)

1. Complete Phase 1: Database schema extension
2. **STOP and VALIDATE**: Test is_etf field exists and can be queried
3. Deploy database migration

### Incremental Delivery

1. **MVP**: Phase 1 (Database field) - Basic ETF identification ready
2. **Increment 1**: Phase 2 (ETF List Sync) - ETFs can be fetched and stored
3. **Increment 2**: Phase 3 (Query Support) - ETFs can be filtered/queried
4. **Increment 3**: Phase 4 (Price Sync) - ETF prices available
5. **Increment 4**: Phase 5 (API Routes) - ETF data accessible via API
6. Each phase adds value without breaking previous functionality

### Team Strategy

With multiple developers:

1. **Phase 1**: Single developer (database schema, blocking dependency)
2. **Phase 2**: Once Phase 1 is complete:
   - Developer A: T008-T011 (ETF API fetcher)
   - Developer B: T012-T019 (ETF sync service)
3. **Phase 4**: Once Phase 2 is complete:
   - Developer A: T027-T030 (ETF price API)
   - Developer B: T031-T040 (ETF price sync)
4. **Phase 5**: Parallel development of different endpoints

---

## Task Summary

- **Total Tasks**: 70
- **Foundation Tasks**: 7 (Phase 1)
- **User Story 1 Tasks**: 13 (Phase 2)
- **User Story 2 Tasks**: 6 (Phase 3)
- **User Story 3 Tasks**: 14 (Phase 4)
- **API Integration Tasks**: 13 (Phase 5)
- **Polish Tasks**: 17 (Phase 6)

### Independent Test Criteria

- **US1 (ETF List Sync)**: Can fetch ETF list from API, store with is_etf='Y', prevent duplicates
- **US2 (Query Support)**: Can query ETFs by filtering is_etf='Y' field
- **US3 (Price Sync)**: Can fetch and store ETF price data in stock_daily_data table

### MVP Scope

**Minimum Viable Product**: Phase 1 only (Database schema extension)
- Enables ETF identification in database
- Provides foundation for future ETF features

**Recommended MVP**: Phases 1 + 2 (Database + ETF List Sync)
- Complete ETF list synchronization
- ETFs available in database for querying
- Foundation for price sync

---

## Notes

- All tasks follow strict format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
- [P] tasks = different files, can run in parallel
- [Story] label maps to specific user story for traceability
- Each user story can be independently completed and tested
- Commit after each logical group or phase checkpoint
- Stop at any checkpoint to validate independently
- Avoid cross-phase dependencies that break story independence
