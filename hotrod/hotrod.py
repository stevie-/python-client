#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binary Hot Rod client.

Copyright (c) 2010  Galder Zamarreño
"""

import socket
import struct

import encoder
import decoder
import exceptions

REQ_MAGIC = 0xA0
RES_MAGIC = 0xA1

VERSION_10 = 10
PUT_REQ = 0x01
PUT_RES = 0x02
GET_REQ = 0x03
GET_RES = 0x04

REQ_FMT = ">BBBBBBBBB"
# magic, msgid, opcode, status, topomark
RES_HEADER_FMT = ">BBBBB"
RES_HEADER_LEN = struct.calcsize(RES_HEADER_FMT)
GET_RES_FMT = ">s"
GET_RES_LEN = struct.calcsize(GET_RES_FMT)

class HotRodClient(object):
   def __init__(self, host='127.0.0.1', port=11311):
      self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.s.connect_ex((host, port))

   def stop(self):
      self.s.close()

   def put(self, key, val, lifespan = 0, maxidle = 0):
      return self._doCmd(PUT_REQ, key, val, lifespan, maxidle)

   def get(self, key):
      return self._doCmd(GET_REQ, key, '', 0, 0)

   def _doCmd(self, cmd, key, val, lifespan, maxidle):
      self._sendCmd(cmd, key, val, lifespan, maxidle)
      return self._handleResponse(val)

   def _handleResponse(self, val):
      header = self._readData(RES_HEADER_LEN)
      magic, msgid, opcode, status, topomark = struct.unpack(RES_HEADER_FMT, header)
      assert (magic == RES_MAGIC), "Got magic: %d" % magic

      if val != '':
         if status != 0:
            raise HotRodError(status, rv)
         return status
      else:
         if status == 2:
            return None
         else:
            if status != 0:
               raise HotRodError(status, rv)
            else:
               response = self._readData(GET_RES_LEN)
               value = struct.unpack(GET_RES_FMT, response)
               local_DecodeVarint = decoder._DecodeVarint32
               (length, pos) = local_DecodeVarint(value, 0)
               rv = ""
               while length > 0:
                  data = self.s.recv(length)
                  if data == '':
                     raise exceptions.EOFError("Got empty data (remote died?).")
                  rv += data
                  length -= len(data)
               assert (magic == RES_MAGIC), "Got magic: %d" % magic
               return rv

   def _readData(self, expectedlen):
      data = ""
      datalen = expectedlen
      while len(data) < datalen:
         tmp = self.s.recv(datalen - len(data))
         if tmp == '':
            raise exceptions.EOFError("Got empty data (remote died?).")
         data += tmp
      assert len(data) == datalen
      return data


   def _sendCmd(self, cmd, key, val, lifespan, maxidle):
      msg = struct.pack(REQ_FMT, REQ_MAGIC, 0x01, VERSION_10,
                        cmd, 0, 0, 0x01, 0, 0)
      if val != '':
         self.s.send(msg + encoder._VarintBytes(len(key)) + key +
            encoder._VarintBytes(lifespan) + encoder._VarintBytes(maxidle) +
            encoder._VarintBytes(len(val)) + val)
      else:
         self.s.send(msg + encoder._VarintBytes(len(key)) + key)

class HotRodError(exceptions.Exception):
   """Error raised when a command fails."""

   def __init__(self, status, msg):
      supermsg = 'Hot Rod error #' + `status`
      if msg: supermsg += ":  " + msg
      exceptions.Exception.__init__(self, supermsg)

      self.status = status
      self.msg = msg

   def __repr__(self):
      return "<Hot Rod error #%d ``%s''>" % (self.status, self.msg)
