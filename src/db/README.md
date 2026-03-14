# Project Auricle Database Usage

## SQLAlchemy Models vs. LangGraph State Persistence

It is important to understand the distinction between the two types of databases used in this project.

1.  **Application Data (SQLAlchemy)**: The models defined in `src/db/models/base.py` are used for long-term relational data. This includes recurring User Settings, API configurations, or logs of historical interactions that need structured querying.
2.  **Agent Memory (LangGraph PostgresSaver)**: The active thought process of the Auricle AI agent is stored as a graph `AgentState`. This is **NOT** stored using SQLAlchemy. Instead, it is persisted directly into hidden, checkpointer-managed Postgres tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`). This is wired up automatically in `src/core/graph.py` passing the `DATABASE_URL`.

## 🕰️ Time Travel Debugging (State Persistence)

Because LangGraph saves the exact state of the agent at every Node step inside Postgres, we can perform "Time Travel Debugging."

This allows us to inspect the state at the exact moment of a failure and "rewind" the conversation to a specific checkpoint ID, or retry a generation with different parameters or fixed code.

### How to Verify State Persistence

To verify that state is successfully saving to your Postgres database:
1. Connect to your `auricle` database via a client like `psql` or DBeaver.
2. Run `\dt` or show the tables. You should see four tables automatically created by `AsyncPostgresSaver`:
   * `checkpoints`
   * `checkpoint_blobs`
   * `checkpoint_writes`
   * `checkpoint_migrations`

### How to Test a "Rewind" or Retry

You can target a specific past graph execution by referencing its `thread_id` and passing it to the checkpointer configuration.

```python
# Assuming you have an instance of AsyncPostgresSaver initialized:
# async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:

# 1. Define the config targeting a specific thread that ran previously
config = {"configurable": {"thread_id": "test_thread_123"}}

# 2. Fetch the exact saved state as it existed at the end of that thread
state = await checkpointer.aget(config)

# 3. Resume, retry, or branched the graph from that exact state
# (You might modify the state dict here before invoking if you are fixing a bug)
final_state = await graph.ainvoke(state, config=config)
```
