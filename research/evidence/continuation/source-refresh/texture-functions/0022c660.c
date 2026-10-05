
void FUN_0022c660(long param_1)

{
  undefined1 uVar1;
  char cVar2;
  undefined1 uVar3;
  short sVar4;
  ulong uVar5;
  ulong uVar6;
  uint uVar7;
  ulong uVar8;
  undefined1 uVar9;
  long lVar10;
  undefined1 uVar11;
  int iVar12;
  int iVar13;
  int iVar14;
  int iVar15;
  int iVar16;
  float fVar17;
  int iVar18;
  
  iVar13 = (int)param_1;
  lVar10 = *(long *)(iVar13 + 0x38);
  uVar1 = (&DAT_00232d92)[(uint)*(byte *)(iVar13 + 0x34) * 0xf];
  iVar14 = 1 << ((uint)((ulong)(lVar10 << 0x11) >> 0x20) & 0xf);
  iVar15 = 1 << ((uint)((ulong)(lVar10 << 0xd) >> 0x20) & 0xf);
  uVar5 = FUN_0022c9f0(uVar1,iVar14,iVar15);
  if (*(ushort *)(iVar13 + 0x30) != uVar5) {
    *(short *)(iVar13 + 0x30) = (short)uVar5;
  }
  iVar16 = 4;
  if (*(char *)(iVar13 + 0x35) == '\0') {
    *(undefined2 *)(iVar13 + 10) = 0;
    iVar16 = 1;
    *(undefined2 *)(iVar13 + 8) = 0;
  }
  else {
    fVar17 = (float)(int)FLOAT_0028eee0;
    *(undefined2 *)(iVar13 + 10) = 0;
    iVar18 = (int)(*(float *)(iVar13 + 0x3c) * 1.4285713 * (fVar17 / (float)iVar14) * 0.5);
    if (iVar18 < 1) {
      iVar18 = 1;
    }
    sVar4 = FUN_00114920(iVar18);
    *(short *)(iVar13 + 8) = sVar4 * -0x10;
  }
  iVar18 = 0;
  uVar7 = 0;
  if (*(char *)(iVar13 + 0x35) != '\0') {
    iVar12 = *(int *)(iVar13 + 0x2c);
    while( true ) {
      iVar14 = iVar14 >> 1;
      iVar15 = iVar15 >> 1;
      iVar12 = iVar12 + iVar18 * 0x10;
      uVar5 = FUN_0022c9f0(uVar1,iVar14,iVar15);
      iVar18 = iVar18 + 1;
      if (*(ushort *)(iVar12 + 2) != uVar5) {
        *(short *)(iVar12 + 2) = (short)uVar5;
      }
      uVar7 = (uint)*(byte *)(iVar13 + 0x35);
      if ((int)uVar7 <= iVar18) break;
      iVar12 = *(int *)(iVar13 + 0x2c);
    }
  }
  uVar8 = 0;
  uVar9 = 0;
  uVar11 = 0;
  cVar2 = (&DAT_00232d91)[(uint)*(byte *)(iVar13 + 0x34) * 0xf];
  uVar5 = uRam00000038;
  uVar1 = 0;
  uVar3 = 0;
  if (param_1 != 0) {
    uVar5 = *(ulong *)(iVar13 + 0x38);
    uVar6 = (long)(uVar5 << 0x17) >> 0x20 & 3;
    if (uVar6 == 1) {
      uVar8 = 1;
      uVar1 = 5;
      uVar3 = 0x40;
    }
    else {
      if (uVar6 != 2) {
        sVar4 = *(short *)(iVar13 + 10);
        goto LAB_0022c840;
      }
      uVar1 = 6;
    }
  }
  uVar11 = uVar3;
  uVar9 = uVar1;
  sVar4 = *(short *)(iVar13 + 10);
LAB_0022c840:
  *(undefined1 *)(iVar13 + 0x36) = uVar9;
  *(undefined1 *)(iVar13 + 0x37) = uVar11;
  uVar8 = uVar5 & 0xfffffffffffffffe | uVar8;
  *(uint *)(iVar13 + 0x18) =
       uVar7 << 2 | (int)sVar4 << 0x13 |
       iVar16 << 6 | ((uint)((ulong)(lVar10 << 0x1b) >> 0x20) & 1) << 5;
  iVar14 = (uint)*(byte *)(iVar13 + 0x34) * 0xf;
  *(int *)(iVar13 + 0x14) = (int)*(short *)(iVar13 + 8);
  *(ulong *)(iVar13 + 0x38) = uVar8;
  uVar7 = (uint)((uVar8 << 0xd) >> 0x20);
  *(uint *)(iVar13 + 0x10) =
       ((uint)((ulong)*(undefined8 *)(iVar13 + 0x30) >> 0x10) & 0x3f) << 0xe | uVar7 << 0x1e |
       ((uint)((uVar8 << 0x11) >> 0x20) & 0xf) << 0x1a | (uint)(byte)(&DAT_00232d99)[iVar14] << 0x14
  ;
  uVar7 = (int)(uVar7 & 0xf) >> 2;
  if (cVar2 == '\0') {
    *(uint *)(iVar13 + 0xc) = uVar7 | 4;
  }
  else {
    *(uint *)(iVar13 + 0xc) = uVar7 | (uint)(byte)(&DAT_00232d9a)[iVar14] << 0x13 | 0x20000004;
  }
  return;
}

