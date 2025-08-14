# Symbolic Control

## Steps to set up the localization server

1. Make sure that both the arena cameras and the Motive program are up and running.
2. Make sure that all rigid bodies - the DeepRacer, targets, and obstacles - are added to the arena. Rigid bodies are added individually by first centering them in the arena, then adding them through the Motive program. 
3. The server is run using the [OptiTrackRESTServer application](https://github.com/HyConSys/OptiTrackRESTServer).
4. The URL for the localization server is: http://192.168.1.194:12345/OptiTrackRestServer

## Steps to set up the symbolic control server

1. Run the closedloop_online example for symbolic control. The steps for this can be found in the section below showing how to connect to the DeepRacer.
2. The URL for the symbolic control server is: http://CUBLabMediaServer:12345/12345/pFaces/REST/dictionary/DeepRacer1

### To connect to the DeepRacer

In a terminal window, run the following lines:

```
$ ssh deepracer@192.168.1.70
$ source /opt/aws/deepracer/setup.sh
$ python put_best_cal.py
$ python sym_control/closedloop_online.py
```

##

A video displaying the lab along with how the DeepRacer works with this symbolic control example can be found [here](https://www.youtube.com/watch?v=a40LoPfL0Z4). 
