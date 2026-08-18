# DCHAG scaling protocol v1.0

Frozen before execution of the dedicated scaling grid.

The scaling study characterizes the reference intervention engine. It is not a causal-accuracy comparison and it is not used to tune the main experiment.

- Graph-size axis: 12, 25, 50, 100, 200, 400 attack-state nodes, plus one context variable and four controls; horizon 4; 20,000 Monte Carlo trajectories for one intervention-effect query.
- Event-count axis: 250, 1,000, and 3,000 prospective trajectories, horizon 4, 50 Monte Carlo replicas per trajectory, fixed 50 attack-state nodes and four controls. Event rows are trajectory × horizon.
- Candidate-control axis: 1, 4, 8, and 16 controls, fixed 50 attack-state nodes and 10,000 Monte Carlo trajectories per control; total time is measured for evaluating all candidate controls.
- Each setting runs in an independent subprocess so peak RSS is setting-specific.
- Seeds are deterministic functions of the axis and setting.
- Report wall-clock seconds and process peak RSS; no failed setting is removed.
