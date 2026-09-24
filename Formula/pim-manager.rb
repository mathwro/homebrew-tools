class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.3/pim-manager_0.1.3_darwin_arm64.tar.gz"
      sha256 "64e51aed9e33c0b8aab47ddfcc7b7af649ee36f4520b9bb793fe5292dc9aa169"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.3/pim-manager_0.1.3_darwin_amd64.tar.gz"
      sha256 "7d867695ed835ed8d842d74c6f50cff9b8115f0159799e781d8eda462a236f17"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.3/pim-manager_0.1.3_linux_arm64.tar.gz"
      sha256 "b10d25cb0bc5efd911908ac72a2fd6886c8d4825871e20edefe050f97ad333a4"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.3/pim-manager_0.1.3_linux_amd64.tar.gz"
      sha256 "b374f706c40fb032826395b9ac5a05495d39b7acc248364a5a38f5fab0b36f5e"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
