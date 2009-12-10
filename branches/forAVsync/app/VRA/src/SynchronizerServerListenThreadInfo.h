/*---------------------------------------------------------------------------*/
/* Volume Rendering Application                                              */
/* Copyright (C) 2006-2007 Nicholas Schwarz                                  */
/*                                                                           */
/* This software is free software; you can redistribute it and/or modify it  */
/* under the terms of the GNU Lesser General Public License as published by  */
/* the Free Software Foundation; either Version 2.1 of the License, or       */
/* (at your option) any later version.                                       */
/*                                                                           */
/* This software is distributed in the hope that it will be useful, but      */
/* WITHOUT ANY WARRANTY; without even the implied warranty of                */
/* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser   */
/* General Public License for more details.                                  */
/*                                                                           */
/* You should have received a copy of the GNU Lesser Public License along    */
/* with this library; if not, write to the Free Software Foundation, Inc.,   */
/* 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA                     */
/*---------------------------------------------------------------------------*/

#ifndef SYNCHRONIZER_SERVER_LISTEN_THREAD_INFO_H
#define SYNCHRONIZER_SERVER_LISTEN_THREAD_INFO_H

/*---------------------------------------------------------------------------*/

#include <pthread.h>
#include <stdlib.h>

#include "SynchronizerServerAbstractCommand.h"
#include "SynchronizerServerClientThreadInfo.h"

/*---------------------------------------------------------------------------*/

class SynchronizerServerListenThreadInfo {

public:

  // Default constructor
  SynchronizerServerListenThreadInfo();

  // Default destructor
  ~SynchronizerServerListenThreadInfo();

  // Client thread info
  SynchronizerServerClientThreadInfo* _clientInfo;

  // Client thread
  pthread_t* _clientThread;

  // Condition mutex
  pthread_mutex_t* _conditionMutex;

  // Condition variable
  pthread_cond_t* _conditionVariable;

  // Finalize flag
  bool* _finalizeFlag;

  // Current level
  int* _level;

  // Number of clients connected
  int* _numberOfClients;

  // Number of clients waiting at barrier
  int* _numberOfClientsWaiting;

  // Server port
  int* _port;

  // Progress observer
  SynchronizerServerAbstractCommand* _progressObserver;

  // Server address
  struct sockaddr_in* _serverAddress;

  // Server socket file descriptor
  int* _serverSocketFileDescriptor;

};

/*---------------------------------------------------------------------------*/

#endif

/*---------------------------------------------------------------------------*/
