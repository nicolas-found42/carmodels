
void FUN_00128518(float param_1,float param_2,float param_3,float param_4,int param_5,int param_6,
                 float param_7,float param_8,undefined8 param_9,undefined8 param_10,
                 undefined8 param_11)

{
  undefined1 in_zero_qw [16];
  undefined1 auVar1 [16];
  undefined1 auVar2 [16];
  undefined1 auVar3 [16];
  undefined1 auVar4 [16];
  undefined1 auVar5 [16];
  undefined1 auVar6 [16];
  undefined4 *puVar7;
  float fVar8;
  float fVar9;
  float fVar10;
  float fVar11;
  float in_stack_00000000;
  float in_stack_00000008;
  
  param_2 = param_2 * 0.5;
  fVar8 = (float)FUN_00204e10(param_3 * 0.5);
  fVar8 = (param_1 * 0.5) / fVar8;
  fVar9 = (float)FUN_00204e10(param_4 * 0.5);
  auVar2 = _pextlw(0,0);
  auVar3 = _por(in_zero_qw,auVar2);
  fVar10 = (in_stack_00000000 * param_1 * 0.5) / fVar8;
  auVar4 = _pextlw((long)param_6,(long)param_5);
  fVar11 = (in_stack_00000000 * param_2) / (param_2 / fVar9);
  auVar1 = _pextlw(0x3f800000,(long)(int)((param_8 + param_7) * 0.5));
  auVar5 = _pcpyld(auVar1,auVar4);
  auVar6 = _pextlw(0,(long)(int)((param_7 - param_8) * 0.5));
  auVar4 = _por(in_zero_qw,auVar2);
  auVar1 = _pextlw(0,(long)(int)((in_stack_00000008 * in_stack_00000000 * -2.0) /
                                (in_stack_00000008 - in_stack_00000000)));
  auVar1 = _pcpyld(auVar1,auVar4);
  puVar7 = (undefined4 *)param_10;
  puVar7[0xc] = auVar1._0_4_;
  puVar7[0xd] = auVar1._4_4_;
  puVar7[0xe] = auVar1._8_4_;
  puVar7[0xf] = auVar1._12_4_;
  auVar4 = _pextlw((long)(int)((-(param_2 / fVar9) * fVar11) / in_stack_00000000),0);
  auVar1 = _pextlw(0x3f800000,
                   (long)(int)((in_stack_00000008 + in_stack_00000000) /
                              (in_stack_00000008 - in_stack_00000000)));
  auVar1 = _pcpyld(auVar1,auVar3);
  puVar7[8] = auVar1._0_4_;
  puVar7[9] = auVar1._4_4_;
  puVar7[10] = auVar1._8_4_;
  puVar7[0xb] = auVar1._12_4_;
  auVar3 = _pcpyld(auVar2,auVar4);
  auVar1 = _pextlw(0,(long)(int)((fVar8 * fVar10) / in_stack_00000000));
  auVar4 = _pcpyld(auVar2,auVar1);
  auVar1 = _pextlw(0,(long)(int)(in_stack_00000000 / fVar10));
  auVar1 = _pcpyld(auVar2,auVar1);
  *puVar7 = auVar1._0_4_;
  puVar7[1] = auVar1._4_4_;
  puVar7[2] = auVar1._8_4_;
  puVar7[3] = auVar1._12_4_;
  auVar1 = _pextlw((long)(int)(in_stack_00000000 / fVar11),0);
  auVar1 = _pcpyld(auVar2,auVar1);
  auVar2 = _pcpyld(auVar6,auVar2);
  puVar7[4] = auVar1._0_4_;
  puVar7[5] = auVar1._4_4_;
  puVar7[6] = auVar1._8_4_;
  puVar7[7] = auVar1._12_4_;
  puVar7 = (undefined4 *)param_11;
  *puVar7 = auVar4._0_4_;
  puVar7[1] = auVar4._4_4_;
  puVar7[2] = auVar4._8_4_;
  puVar7[3] = auVar4._12_4_;
  puVar7[4] = auVar3._0_4_;
  puVar7[5] = auVar3._4_4_;
  puVar7[6] = auVar3._8_4_;
  puVar7[7] = auVar3._12_4_;
  puVar7[8] = auVar2._0_4_;
  puVar7[9] = auVar2._4_4_;
  puVar7[10] = auVar2._8_4_;
  puVar7[0xb] = auVar2._12_4_;
  puVar7[0xc] = auVar5._0_4_;
  puVar7[0xd] = auVar5._4_4_;
  puVar7[0xe] = auVar5._8_4_;
  puVar7[0xf] = auVar5._12_4_;
  FUN_00115560(param_9,param_10,param_11);
  return;
}

