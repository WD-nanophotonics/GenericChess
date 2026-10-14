#define PY_SSIZE_T_CLEAN
#include "native_payload.h"
/* Complete transport only; the existing packer still validates Native state. */
static PyObject *number_attr(PyObject *o,PyObject **names){
 PyObject *v=PyObject_GetAttr(o,names[8]);if(!v)return NULL;
 PyObject *r=PyNumber_Long(v);Py_DECREF(v);return r;
}
static PyObject *typed_lookup(PyObject *map,PyObject *key,const char *message,int chain){
 PyObject *v=PyObject_GetItem(map,key);
 if(!v&&PyErr_ExceptionMatches(PyExc_KeyError)){
  if(chain){
   PyObject *type=NULL,*value=NULL,*traceback=NULL;
   PyErr_Fetch(&type,&value,&traceback);
   PyErr_NormalizeException(&type,&value,&traceback);
   /* Use the exception API, never dispatch into a Python rule callback. */
   PyObject *new_type=NULL,*error=NULL,*new_traceback=NULL;
   PyErr_SetString(PyExc_ValueError,message);
   PyErr_Fetch(&new_type,&error,&new_traceback);
   PyErr_NormalizeException(&new_type,&error,&new_traceback);
   if(error)PyException_SetCause(error,value);
   else Py_XDECREF(value);
   Py_XDECREF(type);Py_XDECREF(traceback);
   PyErr_Restore(new_type,error,new_traceback);
  }else{PyErr_Clear();PyErr_SetString(PyExc_ValueError,message);}
 }
 return v;
}
static PyObject *piece_row(PyObject *p,PyObject *map,PyObject **names){
 PyObject *owner=NULL,*baseid=NULL,*curid=NULL,*prom=NULL,*base=NULL,*cur=NULL,*ownint=NULL,*flag=NULL,*row=NULL;
 owner=PyObject_GetAttr(p,names[0]);if(!owner)goto done;
 int eq0=PyObject_RichCompareBool(owner,Py_False,Py_EQ),eq1=PyObject_RichCompareBool(owner,Py_True,Py_EQ);
 if(eq0<0||eq1<0)goto done;
 if(!eq0&&!eq1){PyErr_SetString(PyExc_ValueError,"Native legality payload has an invalid owner");goto done;}
 baseid=PyObject_GetAttr(p,names[1]);if(!baseid)goto done;
 curid=PyObject_GetAttr(p,names[2]);if(!curid)goto done;
 base=typed_lookup(map,baseid,"Native legality payload has an unknown piece type",1);if(!base)goto done;
 cur=typed_lookup(map,curid,"Native legality payload has an unknown piece type",1);if(!cur)goto done;
 ownint=PyNumber_Long(owner);if(!ownint)goto done;
 prom=PyObject_GetAttr(p,names[3]);if(!prom)goto done;
 int truth=PyObject_IsTrue(prom);if(truth<0)goto done;flag=PyLong_FromLong(truth?1:0);if(!flag)goto done;
 row=PyList_New(4);if(!row)goto done;
 PyList_SET_ITEM(row,0,base);base=NULL;PyList_SET_ITEM(row,1,cur);cur=NULL;
 PyList_SET_ITEM(row,2,ownint);ownint=NULL;PyList_SET_ITEM(row,3,flag);flag=NULL;
done:
 Py_XDECREF(owner);Py_XDECREF(baseid);Py_XDECREF(curid);Py_XDECREF(prom);Py_XDECREF(base);Py_XDECREF(cur);Py_XDECREF(ownint);Py_XDECREF(flag);return row;
}
PyObject *gc_semantic_core_payload(PyObject *self,PyObject *args){
 PyObject *attribute_names;
 PyObject *names[9];
 PyObject *pos,*map,*plyarg;Py_ssize_t ntypes;
 if(!PyArg_ParseTuple(args,"OOnOO",&pos,&map,&ntypes,&plyarg,&attribute_names))return NULL;
 if(!PyTuple_CheckExact(attribute_names)||PyTuple_GET_SIZE(attribute_names)!=9){PyErr_SetString(PyExc_TypeError,"payload attribute names must be a 9-tuple");return NULL;}
 for(int i=0;i<9;i++){names[i]=PyTuple_GET_ITEM(attribute_names,i);if(!PyUnicode_Check(names[i])){PyErr_SetString(PyExc_TypeError,"payload attribute names must be strings");return NULL;}}
 if(ntypes<0){PyErr_SetString(PyExc_ValueError,"negative type count");return NULL;}
 PyObject *rawboard=NULL,*boardfast=NULL,*rawhands=NULL,*handsfast=NULL,*board=NULL,*hands=NULL,*auxraw=NULL,*aux=NULL,*side=NULL,*ply=NULL,*result=NULL;
 rawboard=PyObject_GetAttr(pos,names[4]);if(!rawboard)goto done;
 boardfast=PySequence_Fast(rawboard,"board must be a sequence");if(!boardfast)goto done;
 Py_ssize_t len=PySequence_Fast_GET_SIZE(boardfast);board=PyList_New(len);if(!board)goto done;
 for(Py_ssize_t i=0;i<len;i++){
  PyObject *p=PySequence_Fast_GET_ITEM(boardfast,i),*r;
  if(p==Py_None){r=Py_NewRef(Py_None);}else{r=piece_row(p,map,names);if(!r)goto done;}
  PyList_SET_ITEM(board,i,r);
 }
 rawhands=PyObject_GetAttr(pos,names[5]);if(!rawhands)goto done;
 handsfast=PySequence_Fast(rawhands,"hands must be a sequence");if(!handsfast)goto done;
 len=PySequence_Fast_GET_SIZE(handsfast);hands=PyList_New(len);if(!hands)goto done;
 for(Py_ssize_t i=0;i<len;i++){
  PyObject *counts=PyList_New(ntypes);if(!counts)goto done;
  for(Py_ssize_t j=0;j<ntypes;j++){PyObject *z=PyLong_FromLong(0);if(!z){Py_DECREF(counts);goto done;}PyList_SET_ITEM(counts,j,z);}
  PyList_SET_ITEM(hands,i,counts);
  PyObject *raw=PyObject_GetAttr(PySequence_Fast_GET_ITEM(handsfast,i),names[6]);
  if(!raw)goto done;
  PyObject *entries=PySequence_Fast(raw,"counts must be a sequence");Py_DECREF(raw);if(!entries)goto done;
  for(Py_ssize_t j=0;j<PySequence_Fast_GET_SIZE(entries);j++){
   PyObject *pair=PySequence_Fast(PySequence_Fast_GET_ITEM(entries,j),"hand count must be a pair");
   if(!pair){Py_DECREF(entries);goto done;}
   if(PySequence_Fast_GET_SIZE(pair)!=2){Py_DECREF(pair);Py_DECREF(entries);PyErr_SetString(PyExc_ValueError,"hand count must be a pair");goto done;}
   PyObject *idx=typed_lookup(map,PySequence_Fast_GET_ITEM(pair,0),"Native legality payload has an unknown hand type",0);
   if(!idx){Py_DECREF(pair);Py_DECREF(entries);goto done;}
   Py_ssize_t index=PyLong_AsSsize_t(idx);Py_DECREF(idx);
   if(index==-1&&PyErr_Occurred()){Py_DECREF(pair);Py_DECREF(entries);goto done;}
   PyObject *count=PyNumber_Long(PySequence_Fast_GET_ITEM(pair,1));Py_DECREF(pair);
   if(!count){Py_DECREF(entries);goto done;}
   PyObject *zero=PyLong_FromLong(0);if(!zero){Py_DECREF(count);Py_DECREF(entries);goto done;}
   int negative=PyObject_RichCompareBool(count,zero,Py_LT);Py_DECREF(zero);
   if(negative<0){Py_DECREF(count);Py_DECREF(entries);goto done;}
   if(negative){Py_DECREF(count);Py_DECREF(entries);PyErr_SetString(PyExc_ValueError,"Native legality payload has a negative hand count");goto done;}
   if(PyList_SetItem(counts,index,count)<0){Py_DECREF(entries);goto done;}
  }
  Py_DECREF(entries);
 }
 auxraw=PyObject_GetAttr(pos,names[7]);if(!auxraw)goto done;
 aux=PySequence_Tuple(auxraw);if(!aux)goto done;
 side=number_attr(pos,names);if(!side)goto done;
 ply=PyNumber_Long(plyarg);if(!ply)goto done;
 result=PyDict_New();if(!result)goto done;
 if(PyDict_SetItemString(result,"side",side)<0||PyDict_SetItemString(result,"ply",ply)<0||PyDict_SetItemString(result,"board",board)<0||PyDict_SetItemString(result,"hands",hands)<0||PyDict_SetItemString(result,"aux_state",aux)<0){Py_CLEAR(result);}
done:
 Py_XDECREF(rawboard);Py_XDECREF(boardfast);Py_XDECREF(rawhands);Py_XDECREF(handsfast);Py_XDECREF(board);Py_XDECREF(hands);Py_XDECREF(auxraw);Py_XDECREF(aux);Py_XDECREF(side);Py_XDECREF(ply);return result;
}
