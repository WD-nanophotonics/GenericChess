/* Isolated readonly feasibility kernel. No old ABI, action, make/unmake or globals.
   Numeric rows come exclusively from compiled Core capture IR.
   Same path-clear occupancy and square-slot equality semantics as existing scalar.
   Unsupported guards are rejected by the Python compiler, never silently omitted. */
#include <stdint.h>
typedef struct {int32_t base,current,owner,promoted;} Cell;
typedef struct {uint32_t source,type,path_offset,path_count,guard_offset,guard_count,clear;} Row;
typedef struct {int32_t slot,owner,ref_kind,absolute,unequal;} Guard;
typedef int (*Poll)(void *);
__declspec(dllexport) int wide_query(uint32_t area, const Cell *board,
 const Row *rows, uint32_t row_count, const uint16_t *paths,
 const Guard *guards,const int32_t *aux,uint32_t target,uint32_t attacker,
 Poll poll,void *context,uint64_t *audit) {
 if(target>=area || attacker>1)return -2;
 audit[0]=audit[1]=audit[2]=audit[3]=0;
 if(poll && poll(context))return -1;
 for(uint32_t j=0;j<row_count;j++){
  audit[0]++;
  if((j&31)==0 && poll && poll(context))return -1;
  const Row *r=&rows[j]; const Cell *a=&board[r->source];
  if(a->owner!=(int)attacker || a->current!=(int)r->type)continue;
  audit[1]++;
  if(poll && poll(context))return -1;
  int eligible=1;
  if(r->clear)for(uint32_t k=0;k<r->path_count;k++){
   audit[2]++;
   if((k&31)==0 && poll && poll(context))return -1;
   if(board[paths[r->path_offset+k]].owner>=0){eligible=0;break;}
  }
  if(!eligible)continue;
  for(uint32_t k=0;k<r->guard_count;k++){
   audit[3]++;
   const Guard *g=&guards[r->guard_offset+k];
   int owner=g->owner<0?0:(int)attacker+1;
   int actual=aux[g->slot*3+owner];
   int expected=g->ref_kind==0?(int)target:g->ref_kind==1?(int)r->source:g->absolute;
   int equal=actual>=0 && actual==expected;
   if(g->unequal?equal:!equal){eligible=0;break;}
  }
  if(eligible)return 1;
 }
 return 0;
}

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <string.h>
typedef struct {uint32_t area,types,slots;Row *rows;uint32_t rows_count;
 uint16_t *paths;uint32_t paths_count;Guard *guards;uint32_t guards_count;
 uint32_t *offsets;PyObject *mapping,*names[4];} Rules;
static void destroy(PyObject *cap){
 Rules *r=PyCapsule_GetPointer(cap,"_wide_readonly_lazy.rules");
 if(r){Py_XDECREF(r->mapping);for(int i=0;i<4;i++)Py_XDECREF(r->names[i]);free(r->rows);free(r->paths);free(r->guards);free(r->offsets);free(r);}
}
static void *copied(const char *p,size_t n){
 void *v=malloc(n?n:1);if(v && n)memcpy(v,p,n);return v;
}
static PyObject *compile_rows(PyObject *self,PyObject *args){
 unsigned n,types,slots;PyObject *mapping; const char *rb,*pb,*gb,*ob;Py_ssize_t rn,pn,gn,on;
 if(!PyArg_ParseTuple(args,"IIIOy#y#y#y#",&n,&types,&slots,&mapping,&rb,&rn,&pb,&pn,&gb,&gn,&ob,&on))return NULL;
 if(n<1||n>24||types<1||types>64||slots>8||rn%sizeof(Row)||pn%2||gn%sizeof(Guard)||on!=(2*n*n+1)*sizeof(uint32_t)){
  PyErr_SetString(PyExc_ValueError,"bad private readonly sizes");return NULL;}
 if(!PyDict_Check(mapping)||PyDict_Size(mapping)!=types){PyErr_SetString(PyExc_ValueError,"bad type map");return NULL;}
 Rules *r=calloc(1,sizeof(*r));if(!r)return PyErr_NoMemory();
 r->area=n*n;r->types=types;r->slots=slots;r->rows_count=rn/sizeof(Row);
 r->paths_count=pn/2;r->guards_count=gn/sizeof(Guard);
 r->rows=copied(rb,rn);r->paths=copied(pb,pn);r->guards=copied(gb,gn);r->offsets=copied(ob,on);
 if(!r->rows||!r->paths||!r->guards||!r->offsets){free(r->rows);free(r->paths);free(r->guards);free(r->offsets);free(r);return PyErr_NoMemory();}
 int valid=r->offsets[0]==0 && r->offsets[2*r->area]==r->rows_count;
 for(uint32_t i=0;i<2*r->area;i++)if(r->offsets[i]>r->offsets[i+1]||r->offsets[i+1]>r->rows_count)valid=0;
 for(uint32_t i=0;i<r->rows_count;i++){
  Row *x=&r->rows[i];
  if(x->source>=r->area||x->type>=r->types||x->clear>1||
   (uint64_t)x->path_offset+x->path_count>r->paths_count||
   (uint64_t)x->guard_offset+x->guard_count>r->guards_count)valid=0;
 }
 for(uint32_t i=0;i<r->paths_count;i++)if(r->paths[i]>=r->area)valid=0;
 for(uint32_t i=0;i<r->guards_count;i++){
  Guard *g=&r->guards[i];
  if(g->slot<0||g->slot>=(int)slots||(g->owner!=-1&&g->owner!=0)||g->ref_kind<0||g->ref_kind>1||g->unequal<0||g->unequal>1)valid=0;
 }
 if(!valid){free(r->rows);free(r->paths);free(r->guards);free(r->offsets);free(r);PyErr_SetString(PyExc_ValueError,"bad private readonly static indices");return NULL;}
 r->mapping=PyDict_Copy(mapping); const char *names[4]={"base_type_id","current_type_id","owner","promoted"};
 for(int i=0;i<4;i++)r->names[i]=PyUnicode_InternFromString(names[i]);
 if(!r->mapping||!r->names[0]||!r->names[1]||!r->names[2]||!r->names[3]){Py_XDECREF(r->mapping);for(int i=0;i<4;i++)Py_XDECREF(r->names[i]);free(r->rows);free(r->paths);free(r->guards);free(r->offsets);free(r);return NULL;}
 return PyCapsule_New(r,"_wide_readonly_lazy.rules",destroy);
}
typedef struct {PyObject *callable,*etype,*evalue,*etrace;uint64_t polls;} Callback;
static int checkpoint(void *context){
 Callback *c=context; c->polls++;
 PyGILState_STATE state=PyGILState_Ensure();
 PyObject *v=PyObject_CallNoArgs(c->callable);
 if(!v)PyErr_Fetch(&c->etype,&c->evalue,&c->etrace);
 Py_XDECREF(v);int failed=v==NULL;PyGILState_Release(state);return failed;
}

/* Immutable complete Python board tuple is the readonly carrier: no position
   projection/cache. For this declared pathclear/slot subset only touched actors
   and path occupancy are read. Other guards decline at compile time. */
static int lazy_poll(PyObject *callable,uint64_t *count){
 if(callable==Py_None)return 0;
 (*count)++;
 /* Allow an actual Python cancellation request to execute between bounded
    groups; no inserted wait/sleep. Query operands are strongly held tuples. */
 Py_BEGIN_ALLOW_THREADS
 Py_END_ALLOW_THREADS
 PyObject *v=PyObject_CallNoArgs(callable);if(!v)return -1;Py_DECREF(v);return 0;
}
static PyObject *query(PyObject *self,PyObject *args){
 PyObject *cap,*board,*auxobj,*callback=Py_None;unsigned target,attacker;
 if(!PyArg_ParseTuple(args,"OOOII|O",&cap,&board,&auxobj,&target,&attacker,&callback))return NULL;
 Rules *r=PyCapsule_GetPointer(cap,"_wide_readonly_lazy.rules");if(!r)return NULL;
 if(target>=r->area||attacker>1||!PyTuple_Check(board)||PyTuple_GET_SIZE(board)!=r->area||(callback!=Py_None&&!PyCallable_Check(callback))){
  PyErr_SetString(PyExc_ValueError,"immutable complete board/query required");return NULL;}
 PyObject *a=PySequence_Fast(auxobj,"aux sequence");if(!a)return NULL;
 int32_t aux[8*3]={0};
 if(PySequence_Fast_GET_SIZE(a)!=r->slots*3){Py_DECREF(a);PyErr_SetString(PyExc_ValueError,"incomplete aux");return NULL;}
 for(uint32_t i=0;i<r->slots*3;i++){
  long v=PyLong_AsLong(PySequence_Fast_GET_ITEM(a,i));if(PyErr_Occurred()){Py_DECREF(a);return NULL;}
  if(v<-1||v>=(long)r->area){Py_DECREF(a);PyErr_SetString(PyExc_ValueError,"aux range");return NULL;}aux[i]=v;
 }
 Py_DECREF(a);
 uint64_t audit[5]={0};int result=0;
 uint32_t start=r->offsets[attacker*r->area+target],end=r->offsets[attacker*r->area+target+1];
 if(lazy_poll(callback,&audit[4]))return NULL;
 for(uint32_t j=start;j<end;j++){
  audit[0]++;
  if(((j-start)&31)==0&&lazy_poll(callback,&audit[4]))return NULL;
  Row *row=&r->rows[j];PyObject *actor=PyTuple_GET_ITEM(board,row->source);
  if(actor==Py_None)continue;
  PyObject *owner=PyObject_GetAttr(actor,r->names[2]);if(!owner)return NULL;
  long actor_owner=PyLong_AsLong(owner);Py_DECREF(owner);if(PyErr_Occurred())return NULL;
  if(actor_owner!=(long)attacker)continue;
  PyObject *type=PyObject_GetAttr(actor,r->names[1]);if(!type)return NULL;
  PyObject *index=PyDict_GetItemWithError(r->mapping,type);Py_DECREF(type);
  if(!index){if(!PyErr_Occurred())PyErr_SetString(PyExc_ValueError,"unknown current type");return NULL;}
  long tid=PyLong_AsLong(index);if(PyErr_Occurred())return NULL;
  if(tid!=(long)row->type)continue;
  audit[1]++;if(lazy_poll(callback,&audit[4]))return NULL;
  int eligible=1;
  if(row->clear)for(uint32_t k=0;k<row->path_count;k++){
   audit[2]++;
   if((k&31)==0&&lazy_poll(callback,&audit[4]))return NULL;
   if(PyTuple_GET_ITEM(board,r->paths[row->path_offset+k])!=Py_None){eligible=0;break;}
  }
  if(!eligible)continue;
  for(uint32_t k=0;k<row->guard_count;k++){
   audit[3]++;Guard *g=&r->guards[row->guard_offset+k];
   int owner=g->owner<0?0:(int)attacker+1;
   int actual=aux[g->slot*3+owner];
   int expected=g->ref_kind==0?(int)target:(int)row->source;
   int equal=actual>=0&&actual==expected;
   if(g->unequal?equal:!equal){eligible=0;break;}
  }
  if(eligible){result=1;break;}
 }
 return Py_BuildValue("(iKKKKK)",result,audit[0],audit[1],audit[2],audit[3],audit[4]);
}
static PyMethodDef methods[]={{"compile",compile_rows,METH_VARARGS,NULL},{"query",query,METH_VARARGS,NULL},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"_wide_readonly_lazy",NULL,-1,methods};
PyMODINIT_FUNC PyInit__wide_readonly_lazy(void){return PyModule_Create(&module);}
