class Azc < Formula
  desc "Fast subscription context switcher for Azure CLI"
  homepage "https://github.com/mathwro/azc"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.4.0/azc_0.4.0_darwin_arm64.tar.gz"
      sha256 "0e7a09599d525e1eb9fdde924e4d9ec472e60a85c9ee954b1d1967b68ca03638"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.4.0/azc_0.4.0_darwin_amd64.tar.gz"
      sha256 "e0c9166b277c069baf73712ea3bdcb24cac2580662ec9f6fe18ecde7dcd54a4e"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.4.0/azc_0.4.0_linux_arm64.tar.gz"
      sha256 "a2afa9196bd1df1d481a2998c5a0370422e094f61301f6089a23e3bf23ab68cc"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.4.0/azc_0.4.0_linux_amd64.tar.gz"
      sha256 "ed62118fe90f691b7863f40096fa1a9eec65cd848c12d2f53fe40ef0d6f460b6"
    end
  end

  def install
    bin.install "azc"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/azc --version")
  end
end
