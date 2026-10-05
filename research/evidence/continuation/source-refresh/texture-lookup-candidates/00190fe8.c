
void FUN_00190fe8(undefined8 param_1,undefined8 param_2)

{
  int iVar1;
  int iVar2;
  int iVar3;
  undefined8 uVar4;
  int *piVar5;
  undefined1 (*pauVar6) [16];
  undefined1 auVar7 [16];
  undefined1 auVar8 [16];
  undefined1 auVar9 [16];
  undefined1 auVar10 [16];
  undefined1 auStack_60 [48];
  undefined1 auStack_30 [16];
  
  piVar5 = (int *)param_1;
  FUN_0011e8c0(*(undefined4 *)(piVar5[1] + 0xe4),param_2,auStack_60);
  pauVar6 = (undefined1 (*) [16])(piVar5[1] + 0x50);
  uVar4 = (**(code **)(&DAT_0023cf98 + *piVar5 * 0x5c))(param_1,2);
  uVar4 = (**(code **)(&DAT_0023cfa4 + *(int *)uVar4 * 0x5c))(uVar4,5);
  uVar4 = (**(code **)(&DAT_0023c2b8 + *(int *)uVar4 * 0x5c))(uVar4,6);
  iVar1 = piVar5[1];
  auVar10 = _lqc2(auStack_30);
  iVar2 = ((int *)uVar4)[1];
  iVar3 = *(int *)(iVar1 + 0xec);
  auVar7 = _sqc2(auVar10);
  *pauVar6 = auVar7;
  if ((iVar3 == 1) && (*(long *)(iVar1 + 0xf0) == 0x100000001)) {
    auVar7 = _lqc2(*(undefined1 (*) [16])(iVar2 + 0x30));
    _vmove(auVar10);
    auVar9 = _lqc2(*(undefined1 (*) [16])(iVar2 + 0x40));
    auVar8 = _lqc2(*(undefined1 (*) [16])(iVar2 + 0x20));
    _vmulabc(auVar8,auVar10);
    _vmaddabc(auVar7,auVar10);
    auVar10 = _vmaddbc(auVar9,auVar10);
    auVar7 = _sqc2(auVar10);
    *pauVar6 = auVar7;
    iVar1 = *(int *)uVar4;
    auVar7 = _lqc2(*(undefined1 (*) [16])(iVar2 + 0x50));
    auVar7 = _vadd(auVar10,auVar7);
    auVar7 = _sqc2(auVar7);
    *pauVar6 = auVar7;
    if (iVar1 == 4) {
      FUN_00191148(uVar4,pauVar6);
    }
  }
  return;
}

