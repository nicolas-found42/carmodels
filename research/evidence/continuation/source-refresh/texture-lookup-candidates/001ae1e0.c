
void FUN_001ae1e0(undefined8 param_1,int param_2)

{
  int iVar1;
  float fVar2;
  undefined4 uVar3;
  float fVar4;
  float fVar5;
  float fVar6;
  float fVar7;
  undefined1 auStack_60 [4];
  undefined4 uStack_5c;
  undefined1 auStack_58 [4];
  float fStack_54;
  
  FUN_001ae3b8();
  iVar1 = *(int *)((int)param_1 + 4);
  fVar7 = 0.0;
  fVar4 = *(float *)(iVar1 + 0xfc);
  fVar5 = *(float *)(iVar1 + 0xec);
  fVar2 = 0.01;
  uVar3 = *(undefined4 *)(param_2 + 0x20);
  fVar6 = *(float *)(param_2 + 0x14);
  FUN_001ad980(fVar5,0,fVar4,fVar4,0.01,param_1,auStack_60,&uStack_5c);
  fVar2 = (float)FUN_001ac380(uStack_5c,fVar4,fVar2,uVar3,param_1,auStack_58,&fStack_54);
  if (0.0 < ABS(fVar5)) {
    fVar7 = fStack_54 / fVar5;
  }
  if ((fVar6 < fVar5) && (fVar6 - fVar5 < fVar2)) {
    fVar2 = fVar6 - fVar5;
  }
  fVar5 = 0.0;
  if (fVar2 < 0.0) {
    *(undefined4 *)(param_2 + 0x18) = 0;
    *(float *)(param_2 + 0x10) = fVar2;
    if (0.0 < fVar7) {
      if (fVar7 < 10000.0) {
        *(float *)(param_2 + 0x10) = fVar2 / fVar7;
      }
      goto LAB_001ae308;
    }
    fVar5 = -fVar4;
  }
  else {
    *(float *)(param_2 + 0x18) = fVar4;
  }
  *(float *)(param_2 + 0x10) = fVar5;
LAB_001ae308:
  *(undefined4 *)(param_2 + 0x34) = 1;
  return;
}

