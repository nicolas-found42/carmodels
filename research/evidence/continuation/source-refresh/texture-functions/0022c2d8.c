
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/3d/ps2/3dobjtex.c:1489 */

int FUN_0022c2d8(int param_1,int param_2,int param_3,int param_4)

{
  ushort uVar1;
  int iVar2;
  int iVar3;
  undefined8 uVar4;
  undefined8 uVar5;
  ushort *puVar6;
  int iVar7;
  int iVar8;
  uint uVar9;
  int *piVar10;
  uint uVar11;
  long lVar12;
  
  param_4 = param_4 + -1;
  iVar3 = FUN_00112318();
  iVar7 = iVar3;
  if (-1 < param_4) {
    piVar10 = (int *)(param_4 * 4 + param_3);
    do {
      iVar2 = *piVar10;
      piVar10 = piVar10 + -1;
      iVar8 = iVar7 + 4;
      param_4 = param_4 + -1;
      iVar7 = iVar7 + 1;
      if (*(int *)(iVar2 + 4) != 1) {
        iVar7 = iVar8;
      }
    } while (-1 < param_4);
  }
  param_2 = param_2 + -1;
  if (-1 < param_2) {
    piVar10 = (int *)(param_2 * 4 + param_1);
    do {
      iVar2 = *piVar10;
      uVar11 = (uint)*(byte *)(iVar2 + 0x35);
      iVar7 = iVar7 + (uint)*(ushort *)(iVar2 + 0x30);
      if (uVar11 != 0) {
        puVar6 = (ushort *)(*(int *)(iVar2 + 0x2c) + 2);
        uVar9 = uVar11;
        do {
          uVar1 = *puVar6;
          puVar6 = puVar6 + 8;
          uVar9 = uVar9 - 1;
          iVar7 = iVar7 + (uint)uVar1;
        } while (uVar9 != 0);
      }
      if ((uVar11 != 0) &&
         ((int)(*(float *)(iVar2 + 0x3c) * 1.4285713 *
               ((float)(int)FLOAT_0028eee0 /
               (float)(1 << ((uint)((ulong)(*(long *)(iVar2 + 0x38) << 0x11) >> 0x20) & 0xf))) * 0.5
               ) < 1)) {
        uVar4 = FUN_00125258(iVar2);
        lVar12 = *(long *)(iVar2 + 0x38);
        uVar5 = FUN_002094b0(*(undefined4 *)(iVar2 + 0x3c));
                    /* WARNING: Subroutine does not return */
        FUN_00105888(0x252fc0,0x5d1,0x253030,uVar4,
                     1 << ((uint)((ulong)(lVar12 << 0x11) >> 0x20) & 0xf),
                     1 << ((uint)((ulong)(lVar12 << 0xd) >> 0x20) & 0xf),uVar5);
      }
      param_2 = param_2 + -1;
      piVar10 = piVar10 + -1;
    } while (-1 < param_2);
  }
  return (iVar7 - iVar3) * 0x100;
}

