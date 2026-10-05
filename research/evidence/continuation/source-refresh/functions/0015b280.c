
undefined8
FUN_0015b280(undefined4 param_1,undefined8 param_2,undefined8 param_3,undefined4 param_4,
            long param_5)

{
  undefined1 *puVar1;
  code *pcVar2;
  undefined4 *puVar3;
  uint uVar4;
  undefined4 uVar5;
  undefined8 uVar6;
  int iVar7;
  int *piVar8;
  float fVar9;
  float fVar10;
  float fVar11;
  undefined1 auStack_b0 [16];
  undefined4 uStack_a0;
  undefined4 uStack_90;
  undefined4 uStack_8c;
  undefined4 uStack_88;
  undefined4 uStack_84;
  undefined4 uStack_80;
  undefined4 uStack_7c;
  undefined8 uStack_78;
  undefined8 uStack_70;
  
  uStack_90 = param_1;
  uStack_8c = param_4;
  FUN_0010ee18(param_5);
  fVar9 = (float)FUN_0015af70(param_2);
  piVar8 = (int *)param_2;
  fVar10 = (float)(**(code **)(&DAT_00236f00 + *piVar8 * 4))(param_2);
  fVar9 = fVar9 / fVar10;
  fVar10 = (float)FUN_0021fd28();
  fVar11 = (float)FUN_00154830(param_2);
  iVar7 = *piVar8;
  if (param_5 < 0) {
    (**(code **)(&DAT_002392f0 + iVar7 * 4))(param_2);
    iVar7 = *piVar8;
  }
  uStack_80 = (**(code **)(&DAT_00239520 + iVar7 * 4))(param_2);
  uStack_88 = (**(code **)(&DAT_00236dc0 + *piVar8 * 4))(param_2);
  uStack_84 = (**(code **)(&DAT_00236e10 + *piVar8 * 4))(param_2);
  uVar5 = (**(code **)(&DAT_002396b0 + *piVar8 * 4))(param_2);
  uStack_a0 = CONCAT13((char)((uint)uVar5 >> 0x18),(int3)((uint)uVar5 >> 8) << 8);
  uStack_a0 = CONCAT31(uStack_a0._1_3_,(char)uVar5);
  auStack_b0._0_4_ = uStack_a0;
  pcVar2 = *(code **)(&DAT_002391b0 + *piVar8 * 4);
  puVar1 = auStack_b0 + 3;
  uVar4 = (uint)puVar1 & 3;
  *(uint *)(puVar1 + -uVar4) =
       *(uint *)(puVar1 + -uVar4) & -1 << (uVar4 + 1) * 8 | uStack_a0 >> (3 - uVar4) * 8;
  uStack_7c = (*pcVar2)(param_2);
  uVar5 = (**(code **)(&DAT_002383a0 + *piVar8 * 4))(param_2);
  uStack_78 = FUN_002094b0(uVar5);
  uVar5 = (**(code **)(&DAT_002383f0 + *piVar8 * 4))(param_2);
  uStack_70 = FUN_002094b0(uVar5);
  uVar5 = (**(code **)(&DAT_002392a0 + *piVar8 * 4))(param_2);
  FUN_002094b0(uVar5);
  FUN_002094b0(fVar10 / fVar11);
  FUN_002094b0(fVar9);
  uVar6 = FUN_00148468(1,0x41,param_3,0x44,param_2,0x3a,0x7d,0x3ff0000000000000);
  puVar3 = *(undefined4 **)((int)uVar6 + 4);
  uVar5 = FUN_00151e38(uVar6);
  *puVar3 = uVar5;
  uVar5 = FUN_00151f10(uVar6);
  puVar3[1] = uVar5;
  uVar5 = FUN_00154780(uVar6);
  puVar3[2] = uVar5;
  uVar5 = FUN_00154830(uVar6);
  puVar3[3] = uVar5;
  return uVar6;
}

