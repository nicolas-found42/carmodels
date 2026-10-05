
void FUN_001c6ec8(float param_1,float param_2,int *param_3,float *param_4)

{
  char cVar1;
  char *pcVar2;
  int iVar3;
  int iVar4;
  undefined1 in_zero_qw [16];
  int iVar5;
  undefined *puVar6;
  undefined4 uVar7;
  undefined4 uVar8;
  undefined1 auVar9 [16];
  int iVar10;
  uint uVar11;
  float fVar12;
  float fVar13;
  float fVar14;
  float fVar15;
  undefined8 uStack_70;
  undefined4 uStack_68;
  undefined4 uStack_64;
  
  pcVar2 = (char *)*param_3;
  cVar1 = *pcVar2;
  if (cVar1 < '\0') {
    puVar6 = (undefined *)0x0;
    iVar5 = iRam000000bc;
  }
  else {
    iVar5 = (cVar1 * 0x14 + (int)cVar1) * 0x10;
    puVar6 = &DAT_00241b40 + iVar5;
    iVar5 = *(int *)(&DAT_00241bfc + iVar5);
  }
  iVar3 = *(int *)(puVar6 + 0xb4);
  uVar11 = 0;
  while( true ) {
    iVar10 = 1;
    if (1 < (int)uVar11) {
      iVar10 = 2;
    }
    param_4[uVar11] = 0.0;
    if (iVar10 == 2) {
      fVar14 = 1.0 - *(float *)(iVar3 + 0x50);
    }
    else {
      fVar14 = *(float *)(iVar3 + 0x50);
    }
    iVar4 = *(int *)(uVar11 * 0x130 + *(int *)(pcVar2 + 0x6f0) + 0x120);
    auVar9 = _pextuw(in_zero_qw,*(undefined1 (*) [16])(iVar4 + 0xa0));
    fVar15 = *(float *)(iVar10 * 4 + iVar5 + 0x18) * *(float *)(iVar4 + 0xec) * 0.10471974;
    fVar14 = *(float *)(iVar10 * 4 + iVar5 + 0x24) * fVar14;
    fVar14 = fVar14 + fVar14;
    fVar13 = ABS((float)param_3[uVar11 + 0x2e] *
                 *(float *)(*(int *)(puVar6 + uVar11 * 4 + 0xcc) + 0x3c) + auVar9._0_4_ +
                 fVar15 * *(float *)(*(int *)(puVar6 + uVar11 * 4 + 0xcc) + 0x34) * FLOAT_002901cc);
    if (fVar15 < 0.0) {
      fVar14 = -fVar14;
    }
    fVar12 = -fVar13;
    if (fVar12 <= fVar14) {
      fVar12 = (float)((int)fVar14 * (uint)(fVar14 < fVar13) |
                      (int)fVar13 * (uint)(fVar14 >= fVar13));
    }
    if ((uVar11 < 2) || (param_2 <= 0.0)) {
      fVar13 = fVar12 * param_1;
    }
    else if (0.0 <= fVar15) {
      fVar13 = param_2 * 0.5 * fVar13;
    }
    else {
      fVar13 = param_2 * fVar13 * -0.5;
    }
    param_4[uVar11] = fVar13;
    if (param_2 == 0.0) {
      if (uVar11 == 0) {
        *param_4 = *param_4 * (1.0 - (float)param_3[0x10] * 0.75);
      }
      else if (uVar11 == 1) {
        param_4[1] = param_4[1] * ((float)param_3[0x10] * 0.75 + 1.0);
      }
    }
    if (*(char *)(uVar11 * 0x130 + *(int *)(pcVar2 + 0x6f0) + 0x80) != '\0') {
      uStack_70._0_4_ = *(undefined4 *)*(undefined1 (*) [16])(pcVar2 + 0x650);
      uStack_70._4_4_ = *(undefined4 *)(pcVar2 + 0x654);
      uVar7 = *(undefined4 *)(pcVar2 + 0x658);
      uVar8 = *(undefined4 *)(pcVar2 + 0x65c);
      auVar9 = _por(in_zero_qw,*(undefined1 (*) [16])(pcVar2 + 0x650));
      uStack_68 = uVar7;
      uStack_64 = uVar8;
      uStack_70 = FUN_001150a8(auVar9._0_8_);
      uStack_68 = uVar7;
      uStack_64 = uVar8;
      FUN_001bfd60(-*(float *)(iVar5 + 0x30) * param_1,*param_3 + 0x490,&uStack_70,0xb,*param_3);
    }
    uVar11 = uVar11 + 1;
    if (3 < (int)uVar11) break;
    pcVar2 = (char *)*param_3;
  }
  return;
}

