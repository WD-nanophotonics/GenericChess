#ifndef DEV_AUX_CAPTURE_DIAG_H
#define DEV_AUX_CAPTURE_DIAG_H
#include <cstdint>
#include <cstdlib>
namespace YaneuraOu { namespace AuxCaptureDiag {
inline const bool GainMode = [](){const char* v=std::getenv("DEV_AUX_CAPTURE_GAIN_MODE");if(!v || (v[0]=='0' && !v[1]))return false;if(v[0]=='1' && !v[1])return true;std::exit(2);return false;}();
inline std::uint64_t C[7]={};
inline void reset(){for(auto& x:C)x=0;}
inline void record(int oldValue,int newValue,int alpha,int oldGain,int newGain){++C[0];C[1]+=oldValue<=alpha;C[2]+=newValue<=alpha;C[3]+=(oldValue<=alpha && newValue>alpha);C[4]+=(oldValue>alpha && newValue<=alpha);C[5]+=newGain>oldGain;C[6]+=newGain<oldGain;}
}}
#endif
