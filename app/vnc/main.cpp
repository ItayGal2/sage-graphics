/*****************************************************************************************
 * VNCViewer for SAGE
 * Copyright (C) 2004 Electronic Visualization Laboratory,
 * University of Illinois at Chicago
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *  * Redistributions in binary form must reproduce the above
 *    copyright notice, this list of conditions and the following disclaimer
 *    in the documentation and/or other materials provided with the distribution.
 *  * Neither the name of the University of Illinois at Chicago nor
 *    the names of its contributors may be used to endorse or promote
 *    products derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
 * LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 * NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * Direct questions, comments etc about VNCViewer for SAGE to www.evl.uic.edu/cavern/forum
 *****************************************************************************************/

#if defined(USE_LIBVNC)
#include <rfb/rfbclient.h>
#else
#include "sgVNCViewer.h"
#include <sys/fcntl.h>
#endif

// headers for SAGE
#include "sail.h"
#include "misc.h"
#include <time.h>
#include <unistd.h>

// Global variables
char *passwd, *server;


// Configuration for SAGE, example:
//	nodeNum 1
//	Init 200 200 1480 1224
//	exec 10.0.8.120 VNCViewer 1
//	nwProtocol tvTcpModule.so

#if defined(WIN32)
LARGE_INTEGER perf_freq;
LARGE_INTEGER perf_start;
#elif defined(__APPLE__)
#include <mach/mach_time.h>
static double perf_conversion = 0.0;
static uint64_t perf_start;
#else
struct timeval tv_start;
#endif

void aInitialize()
{
#if defined(WIN32)
    QueryPerformanceCounter(&perf_start);
    QueryPerformanceFrequency(&perf_freq);
#elif defined(__APPLE__)
    if( perf_conversion == 0.0 )
    {
        mach_timebase_info_data_t info;
        kern_return_t err = mach_timebase_info( &info );

            //Convert the timebase into seconds
        if( err == 0  )
            perf_conversion = 1e-9 * (double) info.numer / (double) info.denom;
    }
        // Start of time
    perf_start = mach_absolute_time();

        // Initialize the random generator
    srand(getpid());
#else
        // Start of time
    gettimeofday(&tv_start,0);
        // Initialize the random generator
    srand(getpid());
#endif
}

double aTime()
// return time since start of process in seconds
{
#if defined(WIN32)
    LARGE_INTEGER perf_counter;
#else
    struct timeval tv;
#endif

#if defined(WIN32)
        // Windows: get performance counter and subtract starting mark
    QueryPerformanceCounter(&perf_counter);
    return (double)(perf_counter.QuadPart - perf_start.QuadPart) / (double)perf_freq.QuadPart;
#elif defined(__APPLE__)
    uint64_t difference = mach_absolute_time(); - perf_start;
    return perf_conversion * (double) difference;
#else
        // UNIX: gettimeofday
    gettimeofday(&tv,0);
    return (double)(tv.tv_sec - tv_start.tv_sec) + (double)(tv.tv_usec - tv_start.tv_usec) / 1000000.0;
#endif
}

// Comment/uncomment to use 24bit or 32bit SAGE application stream
#define VNC_SAGE_USE_24bit 1

#if defined(USE_LIBVNC)
rfbClient* vnc;
#else
sgVNCViewer* vnc;
#endif

#if defined(USE_LIBVNC)

static rfbBool got_data = FALSE;
static void signal_handler(int signal)
{
    rfbClientLog("Cleaning up.\n");
}

static rfbBool resize_func(rfbClient* client)
{
    static rfbBool first=TRUE;
    if(!first) {
        rfbClientLog("I don't know yet how to change resolutions!\n");
        exit(1);
    }
    signal(SIGINT,signal_handler);

    int width=client->width;
    int height=client->height;
    int depth=client->format.bitsPerPixel;
    client->updateRect.x = client->updateRect.y = 0;
    client->updateRect.w = width; client->updateRect.h = height;

    client->frameBuffer = (uint8_t*)malloc(width*height*depth);
    memset(client->frameBuffer, 0, width*height*depth);

    rfbClientLog("Allocate %d bytes: %d x %d x %d\n", width*height*depth, width,height,depth);
    return TRUE;
}

static void frame_func(rfbClient* client)
{
    rfbClientLog("Received a frame\n");
}

static rfbBool position_func(rfbClient* client, int x, int y)
{
    //rfbClientLog("Received a position for %d,%d\n",x,y);
    return TRUE;
}

static char *password_func(rfbClient* client)
{
    char *str = (char*)malloc(64);
    memset(str, 0, 64);
    strncpy(str, passwd, 64);
    return str;
}

static void update_func(rfbClient* client,int x,int y,int w,int h)
{
    rfbPixelFormat* pf=&client->format;
    int bpp=pf->bitsPerPixel/8;
    int row_stride=client->width*bpp;

    got_data = TRUE;

    //rfbClientLog("Received an update for %d,%d,%d,%d.\n",x,y,w,h);
}


#endif

int
main(int argc, char **argv)
{
    int winWidth, winHeight, display;
    sail sageInf; // sail object
    double rate = 10;  //by default stream at 1fps

    aInitialize();

    if (argc < 6)
    {
        fprintf(stderr, "\nUsage> VNCviewer <hostname> <display#> <width> <height> <password> [fps]\n\n");
        exit(0);
    }

        // VNC Init
    server    = strdup(argv[1]);
    display   = atoi(argv[2]);
    winWidth  = atoi(argv[3]);
    winHeight = atoi(argv[4]);
    passwd    = argv[5];
    if (argc > 6)
        rate = atoi(argv[6]);


#if defined(USE_LIBVNC)
    // get a vnc client structure (don't connect yet).
    // bits, channels, bytes
    vnc = rfbGetClient(8,3,4);
    vnc->canHandleNewFBSize = FALSE;
    // to get position update callbacks
    vnc->appData.useRemoteCursor=TRUE;
    //vnc->appData.compressLevel=3;
    //vnc->appData.qualityLevel=5;

    /* open VNC connection */
    vnc->MallocFrameBuffer=resize_func;
    vnc->GotFrameBufferUpdate=update_func;
    vnc->HandleCursorPos=position_func;
    vnc->GetPassword=password_func;
    //client->FinishedFrameBufferUpdate=frame_func;


    int margc = 2;
    char *margv[2];
    margv[0] = strdup("vnc");
    margv[1] = (char*)malloc(256);
    memset(margv[1], 0, 256);
    sprintf(margv[1], "%s:%d", server, display);
    if(!rfbInitClient(vnc,&margc,margv)) {
        printf("usage: %s server:port password\n"
               "VNC client.\n", argv[0]);
        exit(1);
    }
    if (vnc->serverPort==-1)
        vnc->vncRec->doNotSleep = TRUE; /* vncrec playback */

    winWidth  = vnc->width;
    winHeight = vnc->height;

#else

        // Connection to VNC server:
        //	host, display number, x offset, y offset, width, height, passwd
        //	passwd is by default 'evl123' but a different one can be specified so that one will be used
    vnc = new sgVNCViewer(server, display, 0,0,winWidth,winHeight, passwd);
#endif

        // Sage Init
    sailConfig scfg;
    scfg.init("VNCViewer.conf");
    scfg.setAppName("VNCViewer");
    scfg.rank = 0;

    scfg.resX = winWidth;
    scfg.resY = winHeight;

    sageRect renderImageMap;
    renderImageMap.left = 0.0;
    renderImageMap.right = 1.0;
    renderImageMap.bottom = 0.0;
    renderImageMap.top = 1.0;

    scfg.imageMap = renderImageMap;
#if defined(VNC_SAGE_USE_24bit)
    scfg.pixFmt = PIXFMT_888;
#else
    scfg.pixFmt = PIXFMT_8888;
#endif
    scfg.rowOrd = TOP_TO_BOTTOM;
    scfg.master = true;

    sageInf.init(scfg);


        // data pointer
    unsigned char *buffer = 0;
    unsigned char *vncpixels;

    double t1, t2;
    t1 = aTime();

        // Main lopp
    while (1)
    {
#if defined(USE_LIBVNC)
        double now = sage::getTime();
        while ( (sage::getTime() - now) < (1000000/rate)) {
            int i=WaitForMessage(vnc,100000);
            if(i<0) {
                rfbClientLog("VNC error, quit\n");
                sageInf.shutdown();
                exit(0);
            }
            if(i) {
                if(!HandleRFBServerMessage(vnc)) {
                    rfbClientLog("HandleRFBServerMessage quit\n");
                    sageInf.shutdown();
                    exit(0);
                }
            }
        }

        // Copy VNC buffer into SAGE buffer
        buffer    = (unsigned char *) sageInf.getBuffer();
        vncpixels = (unsigned char *) vnc->frameBuffer;

        for (int k =0 ; k<winWidth*winHeight; k++) {
            buffer[3*k + 0] = vncpixels[ 4*k + 0];
            buffer[3*k + 1] = vncpixels[ 4*k + 1];
            buffer[3*k + 2] = vncpixels[ 4*k + 2];
        }


        // SAGE Swap
        sageInf.swapBuffer( );

        // Process SAGE messages
        sageMessage msg;
        if (sageInf.checkMsg(msg, false) > 0) {
            switch (msg.getCode()) {
            case APP_QUIT:
                sageInf.shutdown();
                exit(0);
                break;
            }
        }
#else

        if (!vnc->Step())
        {
            sageInf.shutdown();
            exit(0);
        }

            // if it's been (roughly) xxx second since the last
            // sent frame, send another one
        t2 = aTime();
        if ( (t2-t1) > (1.0/rate) )
        {

                //fprintf(stderr, "Rate: %.2f\n", 1.0/(t2-t1) );
            buffer = (unsigned char *) sageInf.getBuffer();
            vncpixels = (unsigned char *) vnc->Data();
#if defined(VNC_SAGE_USE_24bit)
            for (int k =0 ; k<winWidth*winHeight; k++) {
                buffer[3*k + 0] = vncpixels[ 4*k + 0];
                buffer[3*k + 1] = vncpixels[ 4*k + 1];
                buffer[3*k + 2] = vncpixels[ 4*k + 2];
            }
#else
            memcpy(buffer, (unsigned char *) vnc->Data(), winWidth*winHeight*4);
#endif
            sageInf.swapBuffer( );
            t1 = aTime();
        }

        sageMessage msg;
        if (sageInf.checkMsg(msg, false) > 0) {
            switch (msg.getCode()) {
                case APP_QUIT:
                    exit(0);
                    break;
            }
        }
#endif
    }

    return 1;
}


