#include "evaluate.h"
#include <cstdlib>
#include <sstream>
#include <iostream>
static void aux_material_init() {
 const char* raw=std::getenv("DEV_AUX_SHOGI_VALUES");
 if (!raw) { std::cerr << "Missing DEV_AUX_SHOGI_VALUES" << std::endl; std::exit(2); }
 std::istringstream in(raw); int v[16]={0};
 for(int i=1;i<=14;++i) if(!(in>>v[i]) || (i==8 ? v[i]!=0 : v[i]<32 || v[i]>4096)) std::exit(2);
 int extra; if(in>>extra) std::exit(2);
 if(v[1]!=90) std::exit(2);
 using namespace YaneuraOu;
 for(int c=0;c<2;++c) for(int pt=0;pt<16;++pt) {
  int pc=16*c+pt; int base=(pt>=9 && pt<=14)?pt-8:pt;
  Eval::PieceValue[pc]=v[pt]; Eval::PieceValueM[pc]=(c==0?1:-1)*v[pt];
  Eval::CapturePieceValue[pc]=(pt==0 || pt==8 || pt==15)?0:v[pt]+v[base];
  Eval::ProDiffPieceValue[pc]=(base>=1 && base<=6)?v[base+8]-v[base]:0;
 }
}
