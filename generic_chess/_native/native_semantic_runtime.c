#include "native_semantic_runtime.h"

#include <string.h>

static uint16_t action_to(uint64_t a) { return (uint16_t)(a & 0xffu); }
static uint16_t action_from(uint64_t a) { return (uint16_t)((a >> 8) & 0xffu); }
static uint16_t action_promo(uint64_t a) { return (uint16_t)((a >> 16) & 0xffu); }
static uint16_t action_base(uint64_t a) { return (uint16_t)((a >> 24) & 0xffu); }
static uint8_t action_kind(uint64_t a) { return (uint8_t)((a >> 32) & 0xfu); }
static uint16_t action_pattern(uint64_t a) { return (uint16_t)((a >> 36) & 0xffu); }
static uint16_t action_geometry(uint64_t a) { return (uint16_t)((a >> 44) & 0xfffu); }
static uint16_t action_current(uint64_t a) { return (uint16_t)((a >> 56) & 0xffu); }

static int pattern_has_type(const GCSemPattern *p, uint16_t type) {
    for (uint8_t i = 0; i < p->type_count; i++) if (p->type_indices[i] == type) return 1;
    return 0;
}
static const GCSemAuxSlot *slot_meta(const GCSemanticRules *r, uint16_t id, uint8_t *index) {
    for (uint8_t i = 0; i < r->aux_slot_count; i++) if (r->aux_slots[i].slot_id == id) { if (index) *index = i; return &r->aux_slots[i]; }
    return NULL;
}
static void reset_aux_value(const GCSemAuxSlot *slot, GCSemAuxValue *value, uint8_t board_size) {
    memset(value, 0, sizeof(*value));
    value->kind = slot->value_kind;
    if (slot->initial_kind == 1) { value->has_value = 1; value->bool_value = slot->initial_int; }
    else if (slot->initial_kind == 2) { value->has_value = 1; value->square = (uint16_t)(slot->initial_rank * board_size + slot->initial_file); }
}
static int path_entry(const GCSemGeometry *g, uint8_t owner, uint16_t source, const GCSemPathEntry **out) {
    const GCSemPathOwner *paths = &g->paths[owner];
    for (uint16_t i = 0; i < paths->count; i++) if (paths->entries[i].source == source) { *out = &paths->entries[i]; return 1; }
    return 0;
}
static int target_ok(uint8_t target, const GCPiece *cell, uint8_t side) {
    if (target == 0) return !cell->occupied;
    if (target == 1) return cell->occupied && cell->owner != side;
    if (target == 2) return cell->occupied && cell->owner == side;
    return target == 3;
}
static int path_ok(const GCSemPattern *p, const GCSemPathEntry *e, uint16_t target_index, const GCSemanticPosition *pos, uint8_t side) {
    int count = 0, first = -1, last = -1;
    for (uint16_t i = 0; i < target_index; i++) { const GCPiece *piece = &pos->board[e->squares[i]]; if (!piece->occupied) continue; count++; if (first < 0) first = piece->owner == side ? 0 : 1; last = piece->owner == side ? 0 : 1; }
    for (uint8_t i = 0; i < p->path_count; i++) { const GCSemPathPredicate *q=&p->path[i]; if(q->kind==0 && count!=0)return 0; if(q->kind==1 && (!q->has_count || count!=q->count))return 0; if(q->kind==2 && ((!q->has_lo||count<q->lo)||(!q->has_hi||count>q->hi)))return 0; if(q->kind==3&&q->owner_filter!=2&&first!=(int)q->owner_filter)return 0; if(q->kind==4&&q->owner_filter!=2&&last!=(int)q->owner_filter)return 0; }
    return 1;
}
static int resolve_square(const GCSemSquareRef *ref, const GCSemanticRules *r, const GCSemanticPosition *unused, const GCSemanticPosition *pos, uint8_t side, uint16_t source, uint16_t target, uint16_t *out) {
    (void)unused;
    if (!ref || !out) return 0;
    int base = -1;
    if (ref->kind == 0) base = source;
    else if (ref->kind == 1) base = target;
    else if (ref->kind == 2 && ref->has_square) base = ref->square;
    else if ((ref->kind == 3 || ref->kind == 4) && ref->has_offset) {
        base = ref->kind == 3 ? source : target;
        int file = base % r->board_size, rank = base / r->board_size;
        int df = ref->offset_df, dr = ref->offset_dr;
        if (ref->owner_relative && side == 1) { df = -df; dr = -dr; }
        file += df; rank += dr;
        if (file < 0 || rank < 0 || file >= r->board_size || rank >= r->board_size) return 0;
        base = rank * r->board_size + file;
    } else if (ref->kind == 5 && ref->has_step) {
        int sf = source % r->board_size, sr = source / r->board_size;
        int tf = target % r->board_size, tr = target / r->board_size;
        int df = (tf > sf) - (tf < sf), dr = (tr > sr) - (tr < sr);
        int file = sf + df * ((int)ref->step + 1);
        int rank = sr + dr * ((int)ref->step + 1);
        if (file < 0 || rank < 0 || file >= r->board_size || rank >= r->board_size) return 0;
        base = rank * r->board_size + file;
    } else if (ref->kind == 6 && ref->has_slot) {
        uint8_t index = 0; const GCSemAuxSlot *slot = slot_meta(r, ref->slot_id, &index); if (!slot) return 0;
        uint8_t owner_index = slot->scope == 1 ? (uint8_t)(side + 1) : 0;
        const GCSemAuxValue *value = &pos->aux[index][owner_index];
        if (!value->has_value || value->kind != 1) return 0;
        base = value->square;
    } else return 0;
    if (base < 0 || base >= r->board_size * r->board_size) return 0;
    *out = (uint16_t)base; return 1;
}
static int resolve_type(const GCSemTypeRef *ref, uint16_t base, uint16_t current, uint16_t *out) {
    if (!ref || !out) return 0;
    if (ref->kind == 0) *out = base;
    else if (ref->kind == 1) *out = current;
    else if (ref->kind == 2 && ref->has_type) *out = ref->type_index;
    else return 0;
    return 1;
}
static int owner_ok(uint8_t owner_code, uint8_t piece_owner, uint8_t side) { return owner_code == 2 || (owner_code == 0 ? piece_owner == side : piece_owner != side); }
static int resolve_square(const GCSemSquareRef *ref, const GCSemanticRules *r, const GCSemanticPosition *unused, const GCSemanticPosition *pos, uint8_t side, uint16_t source, uint16_t target, uint16_t *out);
static int compare_value(uint8_t comparison, int value, int expected) {
    if (comparison == 0) return value == expected;
    if (comparison == 1) return value != expected;
    if (comparison == 2) return value < expected;
    if (comparison == 3) return value <= expected;
    if (comparison == 4) return value > expected;
    if (comparison == 5) return value >= expected;
    return 0;
}
static int spatial_holds(const GCSemSpatial *spatial, const GCSemanticRules *r, const GCSemanticPosition *pos, uint8_t side, uint16_t source, uint16_t target, uint16_t square) {
    if (!spatial || spatial->refs_count == 0) return 1;
    uint16_t ref_square = 0;
    if (!resolve_square(&spatial->refs[0], r, NULL, pos, side, source, target, &ref_square)) return 0;
    int sf = square % r->board_size, sr = square / r->board_size;
    int rf = ref_square % r->board_size, rr = ref_square / r->board_size;
    if (spatial->kind == 0) return sf == rf;
    if (spatial->kind == 1) return sr == rr;
    if (spatial->kind == 2) return square == ref_square;
    if (spatial->kind == 3) return (sf-rf >= -1 && sf-rf <= 1 && sr-rr >= -1 && sr-rr <= 1);
    if (spatial->kind == 5 && spatial->has_zone && spatial->zone_index < r->zone_count) { const GCSemZone *zone=&r->zones[spatial->zone_index]; for(uint16_t i=0;i<zone->count;i++)if(zone->squares[i]==square)return 1; return 0; }
    return 0;
}
static int state_guards_hold(const GCSemanticRules *r, const GCSemanticPosition *pos, const GCSemPattern *pattern, uint8_t side, uint16_t source, uint16_t target, uint16_t action_base_type, uint16_t action_current_type) {
    for (uint8_t gi = 0; gi < pattern->guard_count; gi++) {
        const GCSemStateGuard *g=&pattern->guards[gi]; if (g->location != 0) return 0;
        int count=0;
        for (uint16_t sq=0;sq<r->board_size*r->board_size;sq++) { const GCPiece *piece=&pos->board[sq]; if(!piece->occupied || !owner_ok(g->owner,piece->owner,side))continue; uint16_t want=0; if(g->type_ref.kind==0)want=action_base_type; else if(g->type_ref.kind==1)want=action_current_type; else if(g->type_ref.kind==2&&g->type_ref.has_type)want=g->type_ref.type_index; else if(g->type_ref.kind==3)want=piece->current_type; else return 0; uint16_t actual=g->compare_field==0?piece->base_type:piece->current_type; if(g->type_ref.kind!=3 && actual!=want)continue; if(g->promoted==0 && !piece->promoted)continue; if(g->promoted==1 && piece->promoted)continue; if(g->promoted>2)return 0; if(!spatial_holds(&g->spatial,r,pos,side,source,target,sq))continue; count++; }
        int predicate = g->aggregation == 0 ? count > 0 : compare_value(g->comparison,count,g->value); if (!predicate) return 0;
    }
    return 1;
}
static int slot_guards_hold(const GCSemanticRules *r, const GCSemanticPosition *pos, const GCSemPattern *pattern, uint8_t side, uint16_t source, uint16_t target) {
    for (uint8_t i=0;i<pattern->slot_guard_count;i++) { const GCSemSlotGuard *g=&pattern->slot_guards[i]; uint8_t index=0; const GCSemAuxSlot *slot=slot_meta(r,g->slot_id,&index); if(!slot)return 0; uint8_t owner_index=slot->scope==1?(uint8_t)(side+1):0; const GCSemAuxValue *value=&pos->aux[index][owner_index]; if(g->has_square_ref){uint16_t expected=0;if(!resolve_square(&g->square_ref,r,NULL,pos,side,source,target,&expected))return 0;int equal=value->has_value&&value->kind==1&&value->square==expected;if(g->comparison==0&&!equal)return 0;if(g->comparison==1&&equal)return 0;}else{int actual=value->has_value?value->bool_value:0;if(!value->has_value&&g->has_value&&g->value!=0&&g->comparison==0)return 0;if(g->has_value&&!compare_value(g->comparison,actual,g->value))return 0;} }
    return 1;
}
static int semantic_attacked_by(const GCSemanticRules *r, const GCSemanticPosition *pos, uint16_t target_square, uint8_t attacker) {
    if (target_square >= r->board_size * r->board_size) return 0;
    for (uint16_t pi=0; pi<r->pattern_count; pi++) {
        const GCSemPattern *pattern=&r->patterns[pi];
        for (uint8_t gi=0; gi<pattern->geometry_count; gi++) {
            uint16_t gid=pattern->geometry_indices[gi]; if(gid>=r->geometry_count)continue;
            const GCSemGeometry *geo=&r->geometries[gid]; if(geo->kind==2)continue;
            const GCSemPathOwner *paths=&geo->paths[attacker];
            for (uint16_t si=0; si<r->board_size*r->board_size; si++) {
                const GCPiece *actor=&pos->board[si]; if(!actor->occupied||actor->owner!=attacker||!pattern_has_type(pattern,actor->current_type))continue;
                if(geo->has_atom_source&&geo->atom_source_type!=actor->current_type)continue;
                const GCSemPathEntry *entry=NULL;if(!path_entry(geo,attacker,si,&entry))continue;
                for(uint16_t ti=0;ti<entry->count;ti++)if(entry->squares[ti]==target_square){uint16_t start=geo->min_steps>0?(uint16_t)(geo->min_steps-1):0;if(ti<start)continue;if(!target_ok(pattern->target,&pos->board[target_square],attacker))continue;if(!path_ok(pattern,entry,ti,pos,attacker))continue;if(!state_guards_hold(r,pos,pattern,attacker,si,target_square,actor->base_type,actor->current_type))continue;if(!slot_guards_hold(r,pos,pattern,attacker,si,target_square))continue;return 1;}
            }
        }
    }
    return 0;
}
static int invariants_hold(const GCSemanticRules *r, const GCSemanticPosition *parent, const GCSemanticPosition *child, const GCSemPattern *pattern, uint8_t side, uint16_t source, uint16_t target) {
    for(uint8_t i=0;i<pattern->invariant_count;i++) {
        const GCSemInvariant *inv=&pattern->invariants[i];
        if(inv->kind==0) {
            for(uint16_t sq=0;sq<r->board_size*r->board_size;sq++) if(child->board[sq].occupied&&child->board[sq].owner==side&&r->types[child->board[sq].current_type].is_anchor&&semantic_attacked_by(r,child,sq,1-side)) return 0;
        } else if(inv->kind==1) {
            for(uint16_t j=0;j<inv->refs_count;j++){uint16_t sq=0;if(!resolve_square(&inv->refs[j],r,NULL,parent,side,source,target,&sq))return 0;if(semantic_attacked_by(r,child,sq,1-side))return 0;}
        } else return 0;
    }
    return 1;
}
static int trigger_event_fires(const GCSemanticRules *r, const GCSemanticPosition *pre, const GCSemPattern *pattern, const GCSemTrigger *trigger, uint8_t side, uint8_t perspective, uint16_t source, uint16_t target) {
    uint16_t trigger_square = 0;
    if (!resolve_square(&trigger->square_ref, r, NULL, pre, perspective, source, target, &trigger_square)) return 0;
    for (uint8_t i = 0; i < pattern->effect_count; i++) {
        const GCSemEffect *effect = &pattern->effects[i];
        uint16_t effect_square = 0;
        if (trigger->event == 0 && (effect->kind == 0 || effect->kind == 9) &&
            resolve_square(&effect->from_ref, r, NULL, pre, perspective, source, target, &effect_square) && effect_square == trigger_square) {
            const GCPiece *piece = &pre->board[effect_square];
            if (piece->occupied && owner_ok(trigger->owner, piece->owner, perspective)) return 1;
        }
        if (trigger->event == 1 && effect->kind == 1 &&
            resolve_square(&effect->square_ref, r, NULL, pre, perspective, source, target, &effect_square) && effect_square == trigger_square) {
            const GCPiece *piece = &pre->board[effect_square];
            if (piece->occupied && owner_ok(trigger->owner, piece->owner, perspective)) return 1;
        }
    }
    return 0;
}

static int validate_action(const GCSemanticRules *r, const GCSemanticPosition *p, uint64_t a, const GCSemPattern **pattern_out, const GCSemGeometry **geo_out, uint16_t *source_out, uint16_t *target_out) {
    uint8_t kind=action_kind(a), side=p->side_to_move; uint16_t pattern_i=action_pattern(a), gid=action_geometry(a), source=action_from(a), target=action_to(a), base=action_base(a), current=action_current(a), promo=action_promo(a);
    if ((kind != GC_ACTION_KIND_SEMANTIC_BOARD && kind != GC_ACTION_KIND_SEMANTIC_DROP) || pattern_i >= r->pattern_count || gid >= r->geometry_count || target >= r->board_size*r->board_size) return 0;
    const GCSemPattern *pattern=&r->patterns[pattern_i]; const GCSemGeometry *geo=&r->geometries[gid]; int owns_geo=0; for(uint8_t i=0;i<pattern->geometry_count;i++)if(pattern->geometry_indices[i]==gid)owns_geo=1; if(!owns_geo)return 0;
    if (kind == GC_ACTION_KIND_SEMANTIC_DROP) {
        if (geo->kind != 2 || source != 255 || base >= r->type_count || current >= r->type_count || current != base || !pattern_has_type(pattern, base) || p->board[target].occupied || p->hand_counts[side][base] == 0) return 0;
        const GCSemSquareList *mask=&r->drop_mask[base][side]; int allowed=0; for(uint16_t i=0;i<mask->count;i++)if(mask->squares[i]==target)allowed=1; if(!allowed)return 0;
    } else {
        if (geo->kind == 2 || source >= r->board_size*r->board_size || source == target) return 0;
        const GCPiece *piece=&p->board[source]; if(!piece->occupied || piece->owner!=side || piece->base_type!=base || piece->current_type!=current || !pattern_has_type(pattern,current))return 0;
        if (geo->has_atom_source && geo->atom_source_type != current) return 0;
        const GCSemPathEntry *entry=NULL; if(!path_entry(geo,side,source,&entry))return 0; int found=-1; for(uint16_t i=0;i<entry->count;i++)if(entry->squares[i]==target){found=i;break;} if(found<0)return 0;
        uint16_t start=geo->min_steps>0?(uint16_t)(geo->min_steps-1):0; if((uint16_t)found<start || !target_ok(pattern->target,&p->board[target],side) || !path_ok(pattern,entry,(uint16_t)found,p,side))return 0;
    }
    if (promo != 255) { if(promo>=r->type_count || kind==GC_ACTION_KIND_SEMANTIC_DROP || !r->types[base].is_promotable)return 0; int allowed=0; for(uint8_t i=0;i<r->types[base].promo_target_count;i++)if(r->types[base].promo_targets[i]==promo)allowed=1; if(!allowed)return 0; }
    if (!state_guards_hold(r, p, pattern, side, source, target, base, current) || !slot_guards_hold(r, p, pattern, side, source, target)) return 0;
    if(pattern_out)*pattern_out=pattern; if(geo_out)*geo_out=geo; if(source_out)*source_out=source; if(target_out)*target_out=target; return 1;
}

static int apply_effect(const GCSemanticRules *r, GCSemanticPosition *work, const GCSemanticPosition *pre, const GCSemPattern *unused_pattern, const GCSemEffect *effect, uint8_t side, uint16_t source, uint16_t target, uint16_t action_base_type, uint16_t action_current_type) {
    uint16_t from=0,to=0,square=0,tid=0; GCPiece piece;
    if(effect->kind==0 || effect->kind==9) { if(!resolve_square(&effect->from_ref,r,NULL,pre,side,source,target,&from)||!resolve_square(&effect->to_ref,r,NULL,pre,side,source,target,&to)||!work->board[from].occupied||work->board[to].occupied)return 0; piece=work->board[from]; if(effect->has_piece_type_ref&&!resolve_type(&effect->piece_type_ref,piece.base_type,piece.current_type,&tid))return 0; if(effect->has_piece_type_ref&&piece.base_type!=tid&&piece.current_type!=tid)return 0; if(!owner_ok(effect->piece_owner,piece.owner,side))return 0; work->board[from].occupied=0; work->board[to]=piece; return 1; }
    if(effect->kind==1) { if(!resolve_square(&effect->square_ref,r,NULL,pre,side,source,target,&square)||!work->board[square].occupied)return 0; piece=work->board[square]; if(r->types[piece.current_type].is_anchor)return 0; if(effect->has_piece_type_ref&&!resolve_type(&effect->piece_type_ref,piece.base_type,piece.current_type,&tid))return 0; if(effect->has_piece_type_ref&&piece.base_type!=tid&&piece.current_type!=tid)return 0; if(!owner_ok(effect->piece_owner,piece.owner,side))return 0; if(effect->has_disposition&&effect->disposition==0){if(work->hand_counts[side][piece.base_type]>=GC_MAX_HAND)return 0;work->hand_counts[side][piece.base_type]++;} work->board[square].occupied=0; return 1; }
    if(effect->kind==2) { if(!effect->has_piece_type_ref||!resolve_type(&effect->piece_type_ref,action_base_type,action_current_type,&tid)||work->hand_counts[side][tid]<effect->count)return 0; work->hand_counts[side][tid]-=effect->count; return 1; }
    if(effect->kind==3) { if(!resolve_square(&effect->to_ref,r,NULL,pre,side,source,target,&to)||work->board[to].occupied||!effect->has_piece_type_ref)return 0; if(!resolve_type(&effect->piece_type_ref,action_base_type,action_current_type,&tid)||tid>=r->type_count)return 0; memset(&work->board[to],0,sizeof(GCPiece));work->board[to].occupied=1;work->board[to].owner=side;work->board[to].base_type=tid;work->board[to].current_type=tid;return 1; }
    if(effect->kind==4) { if(!resolve_square(&effect->square_ref,r,NULL,pre,side,source,target,&square)||!work->board[square].occupied||!effect->has_type_ref||!resolve_type(&effect->type_ref,work->board[square].base_type,work->board[square].current_type,&tid)||tid>=r->type_count)return 0;work->board[square].current_type=tid;work->board[square].promoted=tid!=work->board[square].base_type;return 1; }
    return effect->kind>=5 && effect->kind<=8;
}

int gc_semantic_runtime_make_checked(GCSemanticPosition *child, const GCSemanticRules *r, const GCSemanticPosition *parent, uint64_t action) {
    if(!child||!r||!parent||parent->ply>=r->max_ply)return 0; const GCSemPattern *pattern=NULL; const GCSemGeometry *geo=NULL; uint16_t source=0,target=0; if(!validate_action(r,parent,action,&pattern,&geo,&source,&target))return 0; (void)geo;
    GCSemanticPosition work=*parent; uint8_t side=parent->side_to_move;
    for (uint8_t i = 0; i < r->aux_slot_count; i++) if (r->aux_slots[i].lifetime == 1) {
        reset_aux_value(&r->aux_slots[i], &work.aux[i][0], r->board_size);
        if (r->aux_slots[i].scope == 1) {
            reset_aux_value(&r->aux_slots[i], &work.aux[i][1], r->board_size);
            reset_aux_value(&r->aux_slots[i], &work.aux[i][2], r->board_size);
        }
    }
    uint16_t action_base_type=action_base(action), action_current_type=action_current(action);
    for(uint8_t i=0;i<pattern->effect_count;i++) if(!apply_effect(r,&work,parent,NULL,&pattern->effects[i],side,source,target,action_base_type,action_current_type)) return 0;
    uint16_t promo=action_promo(action); if(promo!=255&&action_kind(action)==GC_ACTION_KIND_SEMANTIC_BOARD&&work.board[target].occupied){work.board[target].current_type=promo;work.board[target].promoted=1;}
    if (!invariants_hold(r, parent, &work, pattern, side, source, target)) return 0;
    for (uint16_t i = 0; i < r->trigger_count; i++) {
        const GCSemTrigger *trigger = &r->triggers[i];
        uint8_t slot_index = 0; const GCSemAuxSlot *slot = slot_meta(r, trigger->slot_id, &slot_index); if (!slot) return 0;
        uint8_t first = slot->scope == 1 ? 1 : 0, last = slot->scope == 1 ? 2 : 0;
        for (uint8_t owner_index = first; owner_index <= last; owner_index++) {
            uint8_t perspective = slot->scope == 1 ? (uint8_t)(owner_index - 1) : side;
            if (!trigger_event_fires(r, parent, pattern, trigger, side, perspective, source, target)) continue;
            work.aux[slot_index][owner_index].kind = slot->value_kind;
            work.aux[slot_index][owner_index].has_value = 1;
            work.aux[slot_index][owner_index].bool_value = 0;
        }
    }
    for(uint8_t i=0;i<pattern->effect_count;i++){const GCSemEffect *e=&pattern->effects[i];if(e->kind<5||e->kind>8)continue;uint8_t slot_index=0;const GCSemAuxSlot *slot=slot_meta(r,e->slot_id,&slot_index);if(!slot)return 0;uint8_t owner_index=slot->scope==1?(uint8_t)(side+1):0;GCSemAuxValue *v=&work.aux[slot_index][owner_index];v->kind=slot->value_kind;v->has_value=1;if(e->kind==5)v->bool_value=e->has_value?e->value:0;else if(e->kind==6)v->bool_value=0;else if(e->kind==7){uint16_t sq;if(!resolve_square(&e->square_ref,r,NULL,parent,side,source,target,&sq))return 0;v->square=sq;}else v->has_value=0;}
    work.side_to_move=1-side;work.ply=parent->ply+1;if(work.history_len>=GC_MAX_PLY+1)return 0;char digest[65];if(!gc_semantic_position_key_digest(r,&work,digest))return 0;uint64_t lo=0,hi=0;for(int i=0;i<16;i++){char c=digest[i];uint8_t n=(uint8_t)(c>='0'&&c<='9'?c-'0':c-'a'+10);lo=(lo<<4)|n;}for(int i=16;i<32;i++){char c=digest[i];uint8_t n=(uint8_t)(c>='0'&&c<='9'?c-'0':c-'a'+10);hi=(hi<<4)|n;}work.history_lo[work.history_len]=lo;work.history_hi[work.history_len]=hi;work.history_len++;*child=work;return 1;
}

int gc_semantic_runtime_make_trusted(GCSemanticPosition *position, const GCSemanticRules *rules, uint64_t action, GCSemanticUndo *undo) {
    if (!position || !rules || !undo) return 0;
    GCSemanticPosition child;
    if (!gc_semantic_runtime_make_checked(&child, rules, position, action)) return 0;
    undo->saved = *position;
    *position = child;
    return 1;
}

void gc_semantic_runtime_unmake(GCSemanticPosition *position, const GCSemanticUndo *undo) {
    if (position && undo) *position = undo->saved;
}
