# The Engin

The Engin is a self-contained modular application.

When ran the Engin takes care of the complete application lifecycle:

1. The Engin assembles all Invocations. Only Providers that are required to satisfy
   the Invocations parameters are assembled.
2. All Invocations are run sequentially in the order they were passed in to the Engin.
3. Any Lifecycle Startup defined by Provider that were assembled is ran.
4. The Engin waits for a stop signal, i.e. SIGINT or SIGTERM.
5. Any Lifecyce Shutdown tasks are run, in reverse order to the Startup order.
