"""Inspect actual PNG text metadata/CRC; compressed pixels are not text records.

Rendered scientific figures and their label sources require separate visual QA.
This is scoped to these own plots, not a universal image privacy detector.
"""
import zlib

def inspect_png(raw,patterns):
 assert raw[:8]==b'\x89PNG\r\n\x1a\n';at=8;chunks=[];texts=[]
 def uncompress(data):
  dec=zlib.decompressobj();out=dec.decompress(data,4*1024*1024+1);assert len(out)<=4*1024*1024 and dec.eof and not dec.unconsumed_tail;return out
 while at<len(raw):
  n=int.from_bytes(raw[at:at+4],'big');kind=raw[at+4:at+8];data=raw[at+8:at+8+n];crc=int.from_bytes(raw[at+8+n:at+12+n],'big');assert len(data)==n and zlib.crc32(kind+data)&0xffffffff==crc
  assert kind in(b'IHDR',b'IDAT',b'IEND',b'pHYs',b'PLTE',b'tRNS',b'gAMA',b'cHRM',b'sRGB',b'sBIT',b'bKGD',b'hIST',b'tIME',b'tEXt',b'zTXt',b'iTXt'),'UnreviewedPNGmetadatachunk'
  text=None
  if kind==b'tEXt':text=data
  elif kind==b'zTXt':
   keyword,sep,body=data.partition(b'\0');assert sep and body[:1]==b'\0';text=keyword+b'\0'+uncompress(body[1:])
  elif kind==b'iTXt':
   keyword,sep,body=data.partition(b'\0');assert sep and len(body)>=2;flag,method=body[0],body[1];assert flag in(0,1)and method==0;language,sep,body=body[2:].partition(b'\0');assert sep;translated,sep,body=body.partition(b'\0');assert sep;text=keyword+b'\0'+language+b'\0'+translated+b'\0'+(uncompress(body)if flag else body)
  if text is not None:
   assert not any(rx.search(text)for rx in patterns),'ActualPNGtextmetadatafailed';texts.append(dict(chunk=kind.decode(),text=text.decode('utf-8',errors='strict')))
  chunks.append(kind.decode());at+=n+12
  if kind==b'IEND':break
 assert at==len(raw)and chunks[0]=='IHDR'and chunks[-1]=='IEND'
 return dict(status='PASS_ACTUAL_PNG_TEXT_METADATA_AND_ALL_CHUNK_CRC',chunks=chunks,texts=texts,scope='CompressedIDATnotinterpretedasplaintext; all8renderedfigures+plotlabelsvisuallyreviewedseparately. Rawimagebytesunchanged.')
