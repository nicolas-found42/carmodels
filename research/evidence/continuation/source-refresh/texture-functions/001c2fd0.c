
float FUN_001c2fd0(int param_1)

{
  char cVar1;
  int iVar2;
  ulong uVar3;
  float fVar4;
  float fVar5;
  float fVar6;
  undefined1 auVar7 [16];
  
  iVar2 = FUN_001db0a8(*(undefined1 *)(param_1 + 6));
  fVar4 = *(float *)(param_1 + 0x108) + FLOAT_002901c4;
  fVar6 = *(float *)(iVar2 + 0x20);
  *(float *)(param_1 + 0x108) = fVar4;
  if (0.0 <= fVar4) {
    fVar4 = (float)((int)fVar4 * (uint)(fVar4 < 0.5) | (uint)(fVar4 >= 0.5) * 0x3f000000);
  }
  else {
    fVar4 = 0.0;
  }
  fVar5 = *(float *)(iVar2 + 0xc);
  if (fVar6 != 0.0) {
    fVar6 = fVar6 * (fVar4 + fVar4);
  }
  fVar4 = -fVar5;
  if (fVar4 <= fVar6) {
    fVar4 = (float)((int)fVar6 * (uint)(fVar6 < fVar5) | (int)fVar5 * (uint)(fVar6 >= fVar5));
  }
  auVar7 = _qmtc2(*(float *)(iVar2 + 0x10) * *(float *)(*(int *)(param_1 + 0x120) + 0xf4));
  _vcallms(0x268);
  auVar7 = _qmfc2(auVar7._0_4_);
  *(float *)(param_1 + 0x104) = fVar5 * auVar7._0_4_;
  auVar7 = _qmtc2(*(float *)(iVar2 + 0x18) * *(float *)(*(int *)(param_1 + 0x120) + 0xf4));
  _vcallms(0x268);
  auVar7 = _qmfc2(auVar7._0_4_);
  *(float *)(param_1 + 0x100) = auVar7._0_4_;
  if (0.9 < auVar7._0_4_) {
    *(undefined4 *)(param_1 + 0x100) = 0x3f800000;
  }
  else {
    *(undefined4 *)(param_1 + 0x100) = 0;
  }
  fVar5 = *(float *)(param_1 + 0x104);
  fVar6 = *(float *)(param_1 + 0x100) * *(float *)(iVar2 + 0x14);
  *(float *)(param_1 + 0x100) = fVar6;
  fVar4 = (float)((int)fVar6 * (uint)(fVar5 < fVar6) | (int)fVar5 * (uint)(fVar5 >= fVar6)) - fVar4;
  if (*(int *)(param_1 + 0x114) != 0) {
    uVar3 = FUN_00134970();
    if ((uVar3 != (long)*(char *)(param_1 + 7)) &&
       (cVar1 = FUN_001c3590(uVar3 & 0xffff), ABS(fVar4) < 0.00049999997)) {
      if (*(char *)(param_1 + 6) == cVar1) {
        *(char *)(param_1 + 6) = cVar1;
      }
      else {
        iVar2 = *(int *)(param_1 + 0x120);
        *(char *)(param_1 + 7) = (char)(uVar3 & 0xffff);
        *(undefined4 *)(param_1 + 0x108) = 0;
        *(undefined4 *)(iVar2 + 0xf4) = 0;
        *(undefined4 *)(iVar2 + 0xf0) = 0;
        *(char *)(param_1 + 6) = cVar1;
      }
    }
  }
  return fVar4;
}

