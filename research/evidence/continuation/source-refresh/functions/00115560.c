
void FUN_00115560(undefined1 (*param_1) [16],undefined1 (*param_2) [16],undefined1 (*param_3) [16])

{
  undefined1 auVar1 [16];
  undefined1 auVar2 [16];
  undefined1 auVar3 [16];
  undefined1 auVar4 [16];
  undefined1 auVar5 [16];
  undefined1 auVar6 [16];
  undefined1 auVar7 [16];
  undefined1 auVar8 [16];
  
  auVar4 = _lqc2(param_3[3]);
  auVar3 = _lqc2(*param_3);
  auVar2 = _lqc2(param_3[1]);
  auVar1 = _lqc2(param_3[2]);
  auVar7 = _lqc2(param_2[3]);
  _vmulabc(auVar3,auVar7);
  _vmaddabc(auVar2,auVar7);
  _vmaddabc(auVar1,auVar7);
  auVar8 = _vmaddbc(auVar4,auVar7);
  auVar7 = _lqc2(*param_2);
  _vmulabc(auVar3,auVar7);
  _vmaddabc(auVar2,auVar7);
  _vmaddabc(auVar1,auVar7);
  auVar6 = _vmaddbc(auVar4,auVar7);
  auVar7 = _lqc2(param_2[1]);
  _vmulabc(auVar3,auVar7);
  _vmaddabc(auVar2,auVar7);
  _vmaddabc(auVar1,auVar7);
  auVar5 = _vmaddbc(auVar4,auVar7);
  auVar7 = _lqc2(param_2[2]);
  _vmulabc(auVar3,auVar7);
  _vmaddabc(auVar2,auVar7);
  _vmaddabc(auVar1,auVar7);
  auVar2 = _vmaddbc(auVar4,auVar7);
  auVar1 = _sqc2(auVar8);
  param_1[3] = auVar1;
  auVar1 = _sqc2(auVar6);
  *param_1 = auVar1;
  auVar1 = _sqc2(auVar5);
  param_1[1] = auVar1;
  auVar1 = _sqc2(auVar2);
  param_1[2] = auVar1;
  return;
}

