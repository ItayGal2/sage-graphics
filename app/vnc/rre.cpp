/************************************************************************
 *
 *  Copyright (C) 1999 AT&T Laboratories Cambridge.  All Rights Reserved.
 *
 *  This is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This software is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this software; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307,
 *  USA.
 ************************************************************************/

/*
 * rre.c - handle RRE encoding.
 *
 * This file shouldn't be compiled directly.  It is included multiple times by
 * rfbproto.c, each time with a different definition of the macro BPP.  For
 * each value of BPP, this file defines a function which handles an RRE
 * encoded rectangle with BPP bits per pixel.
 */

#ifdef HandleRREBPP
#undef HandleRREBPP
#endif
#ifdef CARDBPP
#undef CARDBPP
#endif

#define HandleRREBPP CONCAT2E(HandleRRE,BPP)
#define ReceiveRREBPP CONCAT2E(ReceiveRRE,BPP)
#define flushRREBPP CONCAT2E(flushRRE,BPP)
#define CARDBPP CONCAT2E(CARD,BPP)

Bool
VNCViewer::HandleRREBPP (sgVNCViewer *ct, int rx, int ry, int rw, int rh)
{
    rfbRREHeader hdr;
    int i;
    CARDBPP pix;
    rfbRectangle subrect;

    if (!ReadFromRFBServer((char *)&hdr, sz_rfbRREHeader))
        return False;

    hdr.nSubrects = Swap32IfLE(hdr.nSubrects);

    if (!ReadFromRFBServer((char *)&pix, sizeof(pix)))
        return False;
 
    ct->FillToScreen(pix, rx, ry, rw, rh);

    for (i = 0; i < hdr.nSubrects; i++) {
        if (!ReadFromRFBServer((char *)&pix, sizeof(pix)))
            return False;

        if (!ReadFromRFBServer((char *)&subrect, sz_rfbRectangle))
            return False;

        subrect.x = Swap16IfLE(subrect.x);
        subrect.y = Swap16IfLE(subrect.y);
        subrect.w = Swap16IfLE(subrect.w);
        subrect.h = Swap16IfLE(subrect.h);

        ct->FillToScreen(pix, rx + subrect.x, ry + subrect.y,
                         subrect.w, subrect.h);
    }

    return True;
}

