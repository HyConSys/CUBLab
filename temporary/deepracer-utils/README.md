# deepracer-utils
Tools and experiements for the AWS DeepRacer.


## Installation
```
$ git clone https://github.com/HyConSys/deepracer-utils
```


## Initialization
```
$ cd /deepracer-utils
$ source /opt/aws/deepracer/setup.sh
$ python put_best_cal.py
```

## The control loop

The control loop in the [DeepRacerController](https://github.com/HyConSys/deepracer-utils/blob/main/src/DeepRacerController.py) file is responsible for controlling the actions of the DeepRacer. There are two important variables in the calss: ARENA_UB and ARENA_LB. These mark the upper and lower bounds of the arena, respecively. It is important to note that if the arena were to shift out of position for any reason, these coordinates would need to be re-measured, so the DeepRacer will know the bounds of the arena. 

The control loop works by retrieving the location of the DeepRacer from the localization server. It receives the time, the (x, y) coordinates, the current angle, and the current velocity of the DeepRacer. There are a few conditions in which the control loop will exit and hault the DeepRacer's movements. These are:

- The DeepRacer's current position is "untracked".
- The (x, y) coordinates for the DeepRacer's current position, when compared to the upper and lower bounds of the arena, are out of bounds.
- No control actions are received.
- The time exceeds the real-time deadline that has been set. 

If none of these conditions occur, then the DeepRacer will either stop or move, depending on the action it receives.
