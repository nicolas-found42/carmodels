
void FUN_0019a1b8(undefined8 param_1)

{
  char cVar1;
  short sVar2;
  int iVar3;
  int iVar4;
  undefined *puVar5;
  int iVar6;
  int iVar7;
  float *pfVar8;
  float *pfVar9;
  float *pfVar10;
  int iVar11;
  int iVar12;
  float *pfVar13;
  float *pfVar14;
  float *pfVar15;
  float *pfVar16;
  char *pcVar17;
  float fVar18;
  float fVar19;
  float fVar20;
  float afStack_c0 [4];
  float afStack_b0 [4];
  float afStack_a0 [4];
  float afStack_90 [4];
  float afStack_80 [4];
  float afStack_70 [4];
  int iStack_60;
  
  FUN_0020c7fc(afStack_90,0,0x10);
  pfVar16 = afStack_b0;
  FUN_0020c7fc(pfVar16,0,0x10);
  pfVar13 = afStack_a0;
  FUN_0020c7fc(pfVar13,0,0x10);
  iVar3 = *(int *)((int)param_1 + 4);
  afStack_70[0] = *(float *)(iVar3 + 0x100);
  sVar2 = *(short *)(iVar3 + 0x14);
  iVar12 = *(int *)(*(int *)(iVar3 + 0x14c) + 0x17c);
  afStack_70[1] = (float)*(undefined4 *)(iVar3 + 0x100);
  afStack_70[2] = 0.0;
  afStack_70[3] = 0.0;
  if (sVar2 < 0) {
    puVar5 = (undefined *)0x0;
  }
  else {
    puVar5 = &DAT_00241b40 + (sVar2 * 0x14 + (int)sVar2) * 0x10;
  }
  pfVar14 = afStack_70;
  pfVar15 = afStack_80;
  iVar7 = *(int *)(iVar3 + 0x14c);
  fVar19 = FLOAT_0029016c * 0.10471974;
  pfVar8 = (float *)(puVar5 + 0x90);
  iVar11 = 0;
  pfVar9 = pfVar16;
  do {
    iVar6 = 1;
    if (1 < iVar11) {
      iVar6 = 2;
    }
    iVar6 = iVar6 * 4;
    pfVar10 = pfVar13 + iVar11;
    afStack_90[iVar11] = pfVar8[-4] * fVar19;
    iVar4 = *(int *)(iVar6 + iVar7 + 0x194);
    pfVar14[iVar11] = pfVar8[-0xc];
    pfVar15[iVar11] = pfVar8[-8];
    *pfVar9 = pfVar8[-0x10] + *(float *)(iVar4 + 0x28);
    fVar18 = *(float *)(iVar6 + iVar12 + 0xfc);
    afStack_c0[iVar11] = fVar18;
    if ((iVar11 == 0) || (iVar11 == 2)) {
      afStack_c0[iVar11] = -fVar18;
      fVar18 = *(float *)(iVar4 + 0x28);
    }
    else {
      fVar18 = *(float *)(iVar4 + 0x28);
    }
    fVar18 = *(float *)(iVar6 + iVar12 + 0xb4) + fVar18 + fVar18;
    if (*pfVar9 < fVar18) {
      fVar18 = *pfVar9;
    }
    *pfVar9 = fVar18;
    iVar11 = iVar11 + 1;
    pfVar9 = pfVar9 + 1;
    fVar18 = *pfVar8;
    pfVar8 = pfVar8 + 1;
    *pfVar10 = fVar18;
  } while (iVar11 < 4);
  iStack_60 = 0;
  pcVar17 = (char *)(iVar3 + 0x152);
  iVar12 = 0;
  do {
    FUN_0019a728(*pfVar14,afStack_c0[iVar12],*pfVar15,*pfVar16,param_1,iVar12);
    iVar7 = iStack_60 + *(int *)(**(int **)(iVar3 + 0xe0) + 0x6f0);
    iStack_60 = iStack_60 + 0x130;
    fVar19 = *(float *)(*(int *)(iVar7 + 0x120) + 0xec);
    fVar20 = 0.0;
    fVar18 = *pfVar13;
    if (0.0 <= fVar18) {
      fVar20 = (float)((int)fVar18 * (uint)(fVar18 < 1.0) | (uint)(fVar18 >= 1.0) * 0x3f800000);
    }
    *pfVar13 = fVar20;
    fVar18 = *pfVar13;
    pfVar13 = pfVar13 + 1;
    FUN_0019a7b8(afStack_90[iVar12],*pfVar14,fVar18,param_1,iVar12,ABS(fVar19) <= 200.0);
    iVar7 = 1;
    cVar1 = *pcVar17;
    pcVar17 = pcVar17 + 0x1c;
    if (1 < iVar12) {
      iVar7 = 2;
    }
    iVar11 = iVar12 + 1;
    if ('\0' < cVar1) {
      FUN_0019a508(*pfVar14,*pfVar15,*pfVar16,param_1,iVar12,
                   *(undefined4 *)(iVar7 * 4 + *(int *)(*(int *)((int)param_1 + 4) + 0x14c) + 0x194)
                  );
    }
    pfVar16 = pfVar16 + 1;
    pfVar15 = pfVar15 + 1;
    pfVar14 = pfVar14 + 1;
    iVar12 = iVar11;
  } while (iVar11 < 4);
  FUN_0019a9e0(param_1);
  FUN_0019abb0(param_1);
  FUN_0019ae58(param_1);
  return;
}

